"""List directory contents with LLM-generated descriptions.

This command lists files in a directory and uses an LLM to generate
brief descriptions for each file based on its name and content preview.
"""

from pathlib import Path
from typing import Any

from llm_box.cache import generate_cache_key
from llm_box.commands.base import BaseCommand, CommandContext, CommandResult
from llm_box.commands.registry import CommandRegistry


@CommandRegistry.register
class LsCommand(BaseCommand):
    """List files with LLM-generated descriptions."""

    @property
    def name(self) -> str:
        return "ls"

    @property
    def description(self) -> str:
        return "List files with LLM-generated descriptions"

    @property
    def aliases(self) -> list[str]:
        return ["list", "dir"]

    def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
        """Execute the ls command.

        Args:
            ctx: Command context with provider, cache, etc.
            **kwargs: Command arguments:
                - path: Directory to list (default: ".")
                - all_files: Include hidden files (default: False)
                - pattern: Glob pattern to filter files (default: None)

        Returns:
            CommandResult with list of file descriptions.
        """
        path_str = kwargs.get("path", ".")
        all_files = kwargs.get("all_files", False)
        pattern = kwargs.get("pattern")

        # Resolve path
        try:
            dir_path = Path(path_str).resolve()
            if not dir_path.exists():
                return CommandResult.fail(f"Path does not exist: {path_str}")
            if not dir_path.is_dir():
                return CommandResult.fail(f"Not a directory: {path_str}")
        except Exception as e:
            return CommandResult.fail(f"Invalid path: {e}")

        # List files
        try:
            if pattern:
                files = list(dir_path.glob(pattern))
            else:
                files = list(dir_path.iterdir())

            # Filter hidden files unless --all
            if not all_files:
                files = [f for f in files if not f.name.startswith(".")]

            # Sort: directories first, then by name
            files.sort(key=lambda f: (not f.is_dir(), f.name.lower()))

        except PermissionError:
            return CommandResult.fail(f"Permission denied: {path_str}")
        except Exception as e:
            return CommandResult.fail(f"Error listing directory: {e}")

        if not files:
            return CommandResult.ok(
                data={"path": str(dir_path), "files": [], "count": 0},
                message="No files found",
            )

        # Generate descriptions for files
        file_entries = []
        for file_path in files:
            entry = self._describe_file(ctx, file_path)
            file_entries.append(entry)

        return CommandResult.ok(
            data={
                "path": str(dir_path),
                "files": file_entries,
                "count": len(file_entries),
            }
        )

    def _describe_file(self, ctx: CommandContext, file_path: Path) -> dict[str, Any]:
        """Generate a description for a single file.

        Args:
            ctx: Command context.
            file_path: Path to the file.

        Returns:
            Dict with file info and description.
        """
        # Basic file info
        name = file_path.name
        is_dir = file_path.is_dir()
        file_type = "directory" if is_dir else self._get_file_type(file_path)

        # Get file size for files
        try:
            size = file_path.stat().st_size if not is_dir else None
        except OSError:
            size = None

        # Check cache first
        cache_key = generate_cache_key(
            command="ls",
            provider=ctx.provider.provider_type.value,
            model=ctx.provider.model_name,
            extra_params={"path": str(file_path), "is_dir": is_dir},
        )

        cached = None
        if ctx.use_cache:
            cached = ctx.cache.get(cache_key)

        if cached:
            description = cached.response
            from_cache = True
        else:
            # Generate description via LLM
            description = self._generate_description(ctx, file_path, is_dir, file_type)
            from_cache = False

            # Cache the description
            if ctx.use_cache and description:
                ctx.cache.set(
                    key=cache_key,
                    command="ls",
                    provider=ctx.provider.provider_type.value,
                    model=ctx.provider.model_name,
                    response=description,
                )

        return {
            "name": name,
            "type": file_type,
            "size": size,
            "description": description,
            "cached": from_cache,
        }

    def _generate_description(
        self,
        ctx: CommandContext,
        file_path: Path,
        is_dir: bool,
        file_type: str,
    ) -> str:
        """Generate a description using the LLM.

        Args:
            ctx: Command context with provider.
            file_path: Path to describe.
            is_dir: Whether it's a directory.
            file_type: File type string.

        Returns:
            Brief description string.
        """
        # Build prompt based on file type
        if is_dir:
            # For directories, just describe based on name
            prompt = f"""Provide a brief (10 words or less) description of what this directory likely contains based on its name.

Directory name: {file_path.name}

Respond with only the description, no quotes or extra text."""
        else:
            # For files, include a content preview if it's a text file
            content_preview = self._get_content_preview(file_path)

            if content_preview:
                prompt = f"""Provide a brief (10 words or less) description of this file's purpose.

Filename: {file_path.name}
Type: {file_type}
Content preview:
{content_preview}

Respond with only the description, no quotes or extra text."""
            else:
                prompt = f"""Provide a brief (10 words or less) description of this file's likely purpose based on its name.

Filename: {file_path.name}
Type: {file_type}

Respond with only the description, no quotes or extra text."""

        try:
            response = ctx.provider.invoke(prompt)
            # Clean up response (response.content is the string)
            description = response.content.strip().strip('"').strip("'")
            # Truncate if too long
            if len(description) > 100:
                description = description[:97] + "..."
            return description
        except Exception as e:
            if ctx.verbose:
                return f"(Error: {e})"
            return "(Unable to generate description)"

    def _get_file_type(self, file_path: Path) -> str:
        """Get a human-readable file type."""
        suffix = file_path.suffix.lower()
        type_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".toml": "TOML",
            ".md": "Markdown",
            ".txt": "Text",
            ".sh": "Shell script",
            ".bash": "Bash script",
            ".zsh": "Zsh script",
            ".html": "HTML",
            ".css": "CSS",
            ".sql": "SQL",
            ".rs": "Rust",
            ".go": "Go",
            ".java": "Java",
            ".c": "C",
            ".cpp": "C++",
            ".h": "C header",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".r": "R",
            ".ipynb": "Jupyter notebook",
            ".dockerfile": "Dockerfile",
            ".xml": "XML",
            ".csv": "CSV",
            ".env": "Environment",
            ".gitignore": "Git ignore",
            ".dockerignore": "Docker ignore",
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
            return "License"

        return type_map.get(suffix, suffix[1:].upper() if suffix else "file")

    def _get_content_preview(self, file_path: Path, max_chars: int = 500) -> str | None:
        """Get a preview of file contents for text files.

        Args:
            file_path: Path to the file.
            max_chars: Maximum characters to read.

        Returns:
            Content preview string, or None if not readable.
        """
        # Skip binary files based on extension
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

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read(max_chars)
                if len(content) == max_chars:
                    content += "..."
                return content
        except Exception:
            return None
