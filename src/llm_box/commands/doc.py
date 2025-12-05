"""Generate documentation for code using LLM.

This command reads code files and uses an LLM to generate
documentation such as docstrings, README content, or API docs.
"""

from pathlib import Path
from typing import Any

from llm_box.cache import generate_cache_key
from llm_box.commands.base import BaseCommand, CommandContext, CommandResult
from llm_box.commands.registry import CommandRegistry
from llm_box.utils.hashing import hash_content


@CommandRegistry.register
class DocCommand(BaseCommand):
    """Generate documentation for code using LLM."""

    @property
    def name(self) -> str:
        return "doc"

    @property
    def description(self) -> str:
        return "Generate documentation for code"

    @property
    def aliases(self) -> list[str]:
        return ["document", "docs"]

    def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
        """Execute the doc command.

        Args:
            ctx: Command context with provider, cache, etc.
            **kwargs: Command arguments:
                - file: Path to the file to document
                - style: Documentation style (docstring, readme, api)
                - format: Output format (markdown, rst, plain)
                - include_examples: Include usage examples

        Returns:
            CommandResult with generated documentation.
        """
        file_str = kwargs.get("file")
        if not file_str:
            return CommandResult.fail("No file specified")

        style = kwargs.get("style", "docstring")
        doc_format = kwargs.get("format", "markdown")
        include_examples = kwargs.get("include_examples", True)

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
            command="doc",
            provider=ctx.provider.provider_type.value,
            model=ctx.provider.model_name,
            extra_params={
                "file_hash": content_hash,
                "style": style,
                "format": doc_format,
                "include_examples": include_examples,
            },
        )

        cached = None
        if ctx.use_cache:
            cached = ctx.cache.get(cache_key)

        if cached:
            documentation = cached.response
            from_cache = True
        else:
            # Generate documentation via LLM
            documentation = self._generate_documentation(
                ctx, file_path, content, file_type, style, doc_format, include_examples
            )
            from_cache = False

            # Cache the documentation
            if ctx.use_cache and documentation:
                ctx.cache.set(
                    key=cache_key,
                    command="doc",
                    provider=ctx.provider.provider_type.value,
                    model=ctx.provider.model_name,
                    response=documentation,
                )

        return CommandResult.ok(
            data=documentation,
            cached=from_cache,
            file=str(file_path),
            file_type=file_type,
            style=style,
            format=doc_format,
        )

    def _read_file(self, file_path: Path, max_size: int = 100_000) -> str | None:
        """Read file contents."""
        try:
            size = file_path.stat().st_size
            if size > max_size:
                return None
        except OSError:
            return None

        binary_extensions = {
            ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp",
            ".mp3", ".wav", ".ogg", ".flac", ".aac",
            ".mp4", ".avi", ".mkv", ".mov", ".webm",
            ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".pyc", ".pyo", ".class", ".o", ".a",
        }

        if file_path.suffix.lower() in binary_extensions:
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception:
                return None

    def _get_file_type(self, file_path: Path) -> str:
        """Determine file type from extension."""
        ext_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "React JSX",
            ".tsx": "React TSX",
            ".java": "Java",
            ".c": "C",
            ".cpp": "C++",
            ".cc": "C++",
            ".h": "C header",
            ".hpp": "C++ header",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".scala": "Scala",
            ".sh": "Shell script",
            ".bash": "Bash script",
            ".sql": "SQL",
            ".html": "HTML",
            ".css": "CSS",
        }
        return ext_map.get(file_path.suffix.lower(), "code")

    def _generate_documentation(
        self,
        ctx: CommandContext,
        file_path: Path,
        content: str,
        file_type: str,
        style: str,
        doc_format: str,
        include_examples: bool,
    ) -> str:
        """Generate documentation using LLM."""
        # Truncate content if too long
        max_content = 8000
        if len(content) > max_content:
            content = content[:max_content] + "\n\n[... content truncated ...]"

        # Build style-specific instructions
        if style == "readme":
            style_instruction = """Generate README documentation for this file/module.
Include:
- Overview/description
- Features/functionality
- Installation/setup (if applicable)
- Configuration (if applicable)"""
        elif style == "api":
            style_instruction = """Generate API documentation for this file.
Include:
- Module/class description
- Function/method signatures
- Parameter descriptions
- Return value descriptions
- Exceptions/errors"""
        else:  # docstring
            style_instruction = """Generate docstrings/documentation comments for the code.
Include:
- Module-level docstring
- Class docstrings
- Function/method docstrings with parameters and returns"""

        # Build format-specific instructions
        if doc_format == "rst":
            format_instruction = "Use reStructuredText format (Sphinx-compatible)."
        elif doc_format == "plain":
            format_instruction = "Use plain text format."
        else:  # markdown
            format_instruction = "Use Markdown format."

        example_instruction = ""
        if include_examples:
            example_instruction = "\nInclude usage examples where appropriate."

        prompt = f"""Generate documentation for this {file_type} file.

Filename: {file_path.name}

```
{content}
```

{style_instruction}

{format_instruction}{example_instruction}

Provide well-structured, professional documentation that accurately describes the code."""

        response = ctx.provider.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
