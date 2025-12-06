"""Explain why a file or directory exists.

This command uses an LLM to analyze a file or directory and explain
its purpose within the context of the project.
"""

import contextlib
from pathlib import Path
from typing import Any

from llm_box.cache import generate_cache_key
from llm_box.commands.base import BaseCommand, CommandContext, CommandResult
from llm_box.commands.registry import CommandRegistry
from llm_box.utils.hashing import hash_content


@CommandRegistry.register
class WhyCommand(BaseCommand):
    """Explain why a file or directory exists."""

    @property
    def name(self) -> str:
        return "why"

    @property
    def description(self) -> str:
        return "Explain why a file or directory exists"

    @property
    def aliases(self) -> list[str]:
        return ["purpose", "reason"]

    def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
        """Execute the why command.

        Args:
            ctx: Command context with provider, cache, etc.
            **kwargs: Command arguments:
                - path: Path to the file or directory to explain
                - context: Additional context about the project
                - deep: Include deeper analysis (default: False)

        Returns:
            CommandResult with explanation of purpose.
        """
        path_str = kwargs.get("path")
        if not path_str:
            return CommandResult.fail("No path specified")

        project_context = kwargs.get("context", "")
        deep = kwargs.get("deep", False)

        # Resolve path
        try:
            target_path = Path(path_str).resolve()
            if not target_path.exists():
                return CommandResult.fail(f"Path does not exist: {path_str}")
        except Exception as e:
            return CommandResult.fail(f"Invalid path: {e}")

        is_directory = target_path.is_dir()

        # Gather context
        if is_directory:
            context_info = self._gather_directory_context(target_path)
        else:
            context_info = self._gather_file_context(target_path)

        if context_info is None:
            return CommandResult.fail(f"Cannot analyze path: {path_str}")

        # Generate cache key
        cache_key = generate_cache_key(
            command="why",
            provider=ctx.provider.provider_type.value,
            model=ctx.provider.model_name,
            extra_params={
                "path_hash": hash_content(context_info["content_summary"]),
                "deep": deep,
                "context": project_context,
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
                ctx, target_path, context_info, is_directory, deep, project_context
            )
            from_cache = False

            # Cache the explanation
            if ctx.use_cache and explanation:
                ctx.cache.set(
                    key=cache_key,
                    command="why",
                    provider=ctx.provider.provider_type.value,
                    model=ctx.provider.model_name,
                    response=explanation,
                )

        return CommandResult.ok(
            data=explanation,
            cached=from_cache,
            path=str(target_path),
            is_directory=is_directory,
            **context_info.get("metadata", {}),
        )

    def _gather_directory_context(self, dir_path: Path) -> dict[str, Any] | None:
        """Gather context about a directory."""
        try:
            # List files in the directory
            files = []
            dirs = []
            for item in dir_path.iterdir():
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    dirs.append(item.name)
                else:
                    files.append(item.name)

            # Look for common project files
            readme = None
            for readme_name in ["README.md", "README.rst", "README.txt", "README"]:
                readme_path = dir_path / readme_name
                if readme_path.exists():
                    with contextlib.suppress(Exception):
                        readme = readme_path.read_text(encoding="utf-8")[:2000]
                    break

            # Look for package files
            package_files = []
            for pkg_file in ["pyproject.toml", "setup.py", "package.json", "Cargo.toml",
                            "go.mod", "pom.xml", "build.gradle", "Makefile"]:
                if (dir_path / pkg_file).exists():
                    package_files.append(pkg_file)

            content_summary = f"""
Directory: {dir_path.name}
Files: {', '.join(sorted(files)[:20])}
Subdirectories: {', '.join(sorted(dirs)[:10])}
Package files: {', '.join(package_files)}
README preview: {readme[:500] if readme else 'None'}
"""
            return {
                "content_summary": content_summary,
                "metadata": {
                    "file_count": len(files),
                    "dir_count": len(dirs),
                    "has_readme": readme is not None,
                    "package_files": package_files,
                },
            }
        except Exception:
            return None

    def _gather_file_context(self, file_path: Path) -> dict[str, Any] | None:
        """Gather context about a file."""
        try:
            # Read file content
            content = self._read_file(file_path)
            if content is None:
                # For binary files, just use metadata
                content = "[Binary file - content not readable]"

            # Get parent directory context
            parent = file_path.parent
            siblings = [f.name for f in parent.iterdir()
                       if f.is_file() and not f.name.startswith(".")][:10]

            content_summary = f"""
File: {file_path.name}
Extension: {file_path.suffix}
Parent directory: {parent.name}
Sibling files: {', '.join(siblings)}

File content preview:
{content[:3000]}
"""
            return {
                "content_summary": content_summary,
                "metadata": {
                    "extension": file_path.suffix,
                    "parent": parent.name,
                    "sibling_count": len(siblings),
                },
            }
        except Exception:
            return None

    def _read_file(self, file_path: Path, max_size: int = 50_000) -> str | None:
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

    def _generate_explanation(
        self,
        ctx: CommandContext,
        target_path: Path,
        context_info: dict[str, Any],
        is_directory: bool,
        deep: bool,
        project_context: str,
    ) -> str:
        """Generate explanation using LLM."""
        path_type = "directory" if is_directory else "file"

        base_prompt = f"""Explain why this {path_type} exists and what purpose it serves.

{context_info['content_summary']}

{"Additional project context: " + project_context if project_context else ""}

Answer the question: "Why does this {path_type} exist?"

Focus on:
1. The purpose and role of this {path_type}
2. How it fits into the project structure
3. What problem it solves or what functionality it provides"""

        if deep:
            base_prompt += """
4. How it interacts with other parts of the project
5. Common patterns or conventions it follows
6. Any architectural or design decisions it reflects"""

        base_prompt += "\n\nBe concise but informative. Use markdown formatting."

        response = ctx.provider.invoke(base_prompt)
        return response.content if hasattr(response, "content") else str(response)
