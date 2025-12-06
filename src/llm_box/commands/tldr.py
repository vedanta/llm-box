"""Summarize file contents using LLM.

This command reads a file and uses an LLM to provide a concise
TL;DR summary of its contents.
"""

from pathlib import Path
from typing import Any

from llm_box.cache import generate_cache_key
from llm_box.commands.base import BaseCommand, CommandContext, CommandResult
from llm_box.commands.registry import CommandRegistry
from llm_box.utils.hashing import hash_content


@CommandRegistry.register
class TldrCommand(BaseCommand):
    """Summarize file contents using LLM."""

    @property
    def name(self) -> str:
        return "tldr"

    @property
    def description(self) -> str:
        return "Summarize file contents (TL;DR)"

    @property
    def aliases(self) -> list[str]:
        return ["summary", "summarize"]

    def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
        """Execute the tldr command.

        Args:
            ctx: Command context with provider, cache, etc.
            **kwargs: Command arguments:
                - file: Path to the file to summarize
                - lines: Target number of summary lines (default: 5)
                - format: Output format (bullets, paragraph, oneline)

        Returns:
            CommandResult with summary text.
        """
        file_str = kwargs.get("file")
        if not file_str:
            return CommandResult.fail("No file specified")

        lines = kwargs.get("lines", 5)
        output_format = kwargs.get("format", "bullets")

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
            command="tldr",
            provider=ctx.provider.provider_type.value,
            model=ctx.provider.model_name,
            extra_params={
                "file_hash": content_hash,
                "lines": lines,
                "format": output_format,
            },
        )

        cached = None
        if ctx.use_cache:
            cached = ctx.cache.get(cache_key)

        if cached:
            summary = cached.response
            from_cache = True
        else:
            # Generate summary via LLM
            summary = self._generate_summary(
                ctx, file_path, content, file_type, lines, output_format
            )
            from_cache = False

            # Cache the summary
            if ctx.use_cache and summary:
                ctx.cache.set(
                    key=cache_key,
                    command="tldr",
                    provider=ctx.provider.provider_type.value,
                    model=ctx.provider.model_name,
                    response=summary,
                )

        return CommandResult.ok(
            data=summary,
            cached=from_cache,
            file=str(file_path),
            file_type=file_type,
            content_hash=content_hash,
            lines=lines,
            format=output_format,
        )

    def _read_file(self, file_path: Path, max_size: int = 100_000) -> str | None:
        """Read file contents, returning None for binary or oversized files."""
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
            ".zsh": "Zsh script",
            ".sql": "SQL",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".less": "Less",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".toml": "TOML",
            ".xml": "XML",
            ".md": "Markdown",
            ".rst": "reStructuredText",
            ".txt": "text",
        }
        return ext_map.get(file_path.suffix.lower(), "text")

    def _generate_summary(
        self,
        ctx: CommandContext,
        file_path: Path,
        content: str,
        file_type: str,
        lines: int,
        output_format: str,
    ) -> str:
        """Generate summary using LLM."""
        # Truncate content if too long
        max_content = 8000
        if len(content) > max_content:
            content = content[:max_content] + "\n\n[... content truncated ...]"

        # Build format instructions
        if output_format == "oneline":
            format_instruction = "Provide a single sentence summary."
        elif output_format == "paragraph":
            format_instruction = f"Provide a concise paragraph (about {lines} sentences) summarizing the key points."
        else:  # bullets
            format_instruction = f"Provide {lines} bullet points summarizing the key aspects."

        prompt = f"""TL;DR - Summarize this {file_type} file.

Filename: {file_path.name}

```
{content}
```

{format_instruction}

Focus on:
- The main purpose and functionality
- Key components or features
- Important patterns or techniques

Be concise and direct. No preamble or explanation of the task."""

        response = ctx.provider.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
