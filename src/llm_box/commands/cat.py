"""Explain file contents using LLM.

This command reads a file and uses an LLM to provide a detailed
explanation of its contents, structure, and purpose.
"""

from pathlib import Path
from typing import Any

from llm_box.cache import generate_cache_key
from llm_box.commands.base import BaseCommand, CommandContext, CommandResult
from llm_box.commands.registry import CommandRegistry
from llm_box.utils.hashing import hash_content


@CommandRegistry.register
class CatCommand(BaseCommand):
    """Explain file contents using LLM."""

    @property
    def name(self) -> str:
        return "cat"

    @property
    def description(self) -> str:
        return "Explain file contents using LLM"

    @property
    def aliases(self) -> list[str]:
        return ["explain", "describe"]

    def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
        """Execute the cat command.

        Args:
            ctx: Command context with provider, cache, etc.
            **kwargs: Command arguments:
                - file: Path to the file to explain
                - brief: Generate brief summary only (default: False)
                - focus: Specific aspect to focus on (default: None)

        Returns:
            CommandResult with explanation text.
        """
        file_str = kwargs.get("file")
        if not file_str:
            return CommandResult.fail("No file specified")

        brief = kwargs.get("brief", False)
        focus = kwargs.get("focus")

        # Resolve file path
        try:
            file_path = Path(file_str).resolve()
            if not file_path.exists():
                return CommandResult.fail(f"File does not exist: {file_str}")
            if file_path.is_dir():
                return CommandResult.fail(f"Path is a directory: {file_str}")
        except Exception as e:
            return CommandResult.fail(f"Invalid path: {e}")

        # Read file contents
        try:
            content = self._read_file(file_path)
            if content is None:
                return CommandResult.fail(
                    f"Cannot read file (binary or too large): {file_str}"
                )
        except PermissionError:
            return CommandResult.fail(f"Permission denied: {file_str}")
        except Exception as e:
            return CommandResult.fail(f"Error reading file: {e}")

        # Get file metadata
        file_type = self._get_file_type(file_path)
        content_hash = hash_content(content)

        # Check cache
        cache_key = generate_cache_key(
            command="cat",
            provider=ctx.provider.provider_type.value,
            model=ctx.provider.model_name,
            extra_params={
                "file_hash": content_hash,
                "brief": brief,
                "focus": focus or "",
            },
        )

        cached = None
        if ctx.use_cache:
            cached = ctx.cache.get(cache_key)

        if cached:
            explanation = cached.response
            from_cache = True
        else:
            # Generate explanation via LLM
            explanation = self._generate_explanation(
                ctx, file_path, content, file_type, brief, focus
            )
            from_cache = False

            # Cache the explanation
            if ctx.use_cache and explanation:
                ctx.cache.set(
                    key=cache_key,
                    command="cat",
                    provider=ctx.provider.provider_type.value,
                    model=ctx.provider.model_name,
                    response=explanation,
                )

        return CommandResult.ok(
            data=explanation,
            cached=from_cache,
            file=str(file_path),
            file_type=file_type,
            content_hash=content_hash,
        )

    def _read_file(self, file_path: Path, max_size: int = 100_000) -> str | None:
        """Read file contents, returning None for binary or oversized files.

        Args:
            file_path: Path to the file.
            max_size: Maximum file size to read.

        Returns:
            File contents as string, or None if unreadable.
        """
        # Check file size
        try:
            size = file_path.stat().st_size
            if size > max_size:
                return None
        except OSError:
            return None

        # Skip known binary extensions
        binary_extensions = {
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".bin",
            ".dat",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
            ".ico",
            ".webp",
            ".mp3",
            ".wav",
            ".ogg",
            ".flac",
            ".aac",
            ".mp4",
            ".avi",
            ".mkv",
            ".mov",
            ".webm",
            ".zip",
            ".tar",
            ".gz",
            ".bz2",
            ".xz",
            ".7z",
            ".rar",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".pyc",
            ".pyo",
            ".class",
            ".o",
            ".a",
        }

        if file_path.suffix.lower() in binary_extensions:
            return None

        # Try to read as text
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with a more permissive encoding
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception:
                return None

    def _generate_explanation(
        self,
        ctx: CommandContext,
        file_path: Path,
        content: str,
        file_type: str,
        brief: bool,
        focus: str | None,
    ) -> str:
        """Generate explanation using LLM.

        Args:
            ctx: Command context with provider.
            file_path: Path to the file.
            content: File contents.
            file_type: File type string.
            brief: Whether to generate brief summary.
            focus: Specific aspect to focus on.

        Returns:
            Explanation text.
        """
        # Truncate content if too long
        max_content = 8000
        if len(content) > max_content:
            content = content[:max_content] + "\n\n[... content truncated ...]"

        # Build prompt
        if brief:
            if focus:
                prompt = f"""Provide a brief (2-3 sentences) explanation of this {file_type} file, focusing on: {focus}

Filename: {file_path.name}

```
{content}
```

Be concise and focus on the key points related to: {focus}"""
            else:
                prompt = f"""Provide a brief (2-3 sentences) summary of this {file_type} file.

Filename: {file_path.name}

```
{content}
```

Be concise and focus on the main purpose and key components."""
        else:
            if focus:
                prompt = f"""Explain this {file_type} file in detail, with particular focus on: {focus}

Filename: {file_path.name}

```
{content}
```

Provide a comprehensive explanation covering:
1. Main purpose of the file
2. Key components/sections (focusing on {focus})
3. Important patterns or techniques used
4. Any notable dependencies or requirements

Use markdown formatting for clarity."""
            else:
                prompt = f"""Explain this {file_type} file in detail.

Filename: {file_path.name}

```
{content}
```

Provide a comprehensive explanation covering:
1. Main purpose of the file
2. Key components, classes, or functions
3. Important patterns or techniques used
4. Any notable dependencies or requirements
5. Potential improvements or concerns (if any)

Use markdown formatting for clarity."""

        try:
            response = ctx.provider.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            if ctx.verbose:
                return f"Error generating explanation: {e}"
            return f"Unable to generate explanation for {file_path.name}"

    def _get_file_type(self, file_path: Path) -> str:
        """Get a human-readable file type."""
        suffix = file_path.suffix.lower()
        type_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript React",
            ".jsx": "JavaScript React",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".toml": "TOML",
            ".md": "Markdown",
            ".txt": "text",
            ".sh": "shell script",
            ".bash": "Bash script",
            ".zsh": "Zsh script",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".less": "LESS",
            ".sql": "SQL",
            ".rs": "Rust",
            ".go": "Go",
            ".java": "Java",
            ".c": "C",
            ".cpp": "C++",
            ".h": "C/C++ header",
            ".hpp": "C++ header",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".r": "R",
            ".ipynb": "Jupyter notebook",
            ".dockerfile": "Dockerfile",
            ".xml": "XML",
            ".csv": "CSV",
            ".env": "environment configuration",
            ".gitignore": "Git ignore",
            ".dockerignore": "Docker ignore",
            ".editorconfig": "editor configuration",
            ".eslintrc": "ESLint configuration",
            ".prettierrc": "Prettier configuration",
        }

        # Check for special filenames
        name_lower = file_path.name.lower()
        if name_lower == "dockerfile":
            return "Dockerfile"
        if name_lower == "makefile":
            return "Makefile"
        if name_lower.startswith("readme"):
            return "README"
        if name_lower == "license" or name_lower.startswith("license"):
            return "license"
        if name_lower == "pyproject.toml":
            return "Python project configuration"
        if name_lower == "package.json":
            return "Node.js package configuration"
        if name_lower == "cargo.toml":
            return "Rust cargo configuration"

        return type_map.get(suffix, suffix[1:] if suffix else "text")
