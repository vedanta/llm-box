"""File operations utilities."""

from collections.abc import Iterator
from pathlib import Path

# Binary file extensions to skip
BINARY_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".webp",
        ".svg",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".rar",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".mp3",
        ".mp4",
        ".wav",
        ".avi",
        ".mov",
        ".mkv",
        ".pyc",
        ".pyo",
        ".class",
        ".o",
        ".obj",
        ".db",
        ".sqlite",
        ".duckdb",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".eot",
    }
)

# Common hidden/ignored directories
IGNORED_DIRS = frozenset(
    {
        ".git",
        ".svn",
        ".hg",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "venv",
        ".venv",
        "env",
        ".env",
        ".idea",
        ".vscode",
        "dist",
        "build",
        "*.egg-info",
        ".tox",
        ".nox",
        "coverage",
        "htmlcov",
        ".coverage",
    }
)

# Programming language detection by extension
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".r": "r",
    ".R": "r",
    ".lua": "lua",
    ".vim": "vim",
    ".el": "elisp",
    ".clj": "clojure",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".fs": "fsharp",
    ".pl": "perl",
    ".pm": "perl",
}


def is_binary_file(path: Path) -> bool:
    """Check if a file is likely binary based on extension.

    Args:
        path: Path to file.

    Returns:
        True if file appears to be binary.
    """
    return path.suffix.lower() in BINARY_EXTENSIONS


def is_hidden(path: Path) -> bool:
    """Check if a file or directory is hidden.

    Args:
        path: Path to check.

    Returns:
        True if path is hidden (starts with .).
    """
    return path.name.startswith(".")


def should_ignore_dir(name: str) -> bool:
    """Check if a directory should be ignored during traversal.

    Args:
        name: Directory name.

    Returns:
        True if directory should be ignored.
    """
    return name in IGNORED_DIRS or name.startswith(".")


def detect_language(path: Path) -> str | None:
    """Detect programming language from file extension.

    Args:
        path: Path to file.

    Returns:
        Language name or None if unknown.
    """
    return LANGUAGE_MAP.get(path.suffix.lower())


def read_text_safe(
    path: Path,
    max_bytes: int | None = None,
    errors: str = "ignore",
) -> str | None:
    """Safely read text file content.

    Args:
        path: Path to file.
        max_bytes: Maximum bytes to read (None for all).
        errors: How to handle encoding errors.

    Returns:
        File content as string, or None if cannot be read.
    """
    try:
        if max_bytes:
            with open(path, encoding="utf-8", errors=errors) as f:
                return f.read(max_bytes)
        else:
            return path.read_text(encoding="utf-8", errors=errors)
    except Exception:
        return None


def sample_content(path: Path, max_bytes: int = 1000) -> str | None:
    """Get a sample of file content for LLM context.

    Args:
        path: Path to file.
        max_bytes: Maximum bytes to sample.

    Returns:
        Content sample or None if cannot be read.
    """
    if is_binary_file(path):
        return None
    return read_text_safe(path, max_bytes=max_bytes)


def iter_files(
    directory: Path,
    *,
    include_hidden: bool = False,
    skip_binary: bool = True,
    extensions: set[str] | None = None,
    max_depth: int | None = None,
) -> Iterator[Path]:
    """Iterate over files in a directory.

    Args:
        directory: Root directory to search.
        include_hidden: Include hidden files/directories.
        skip_binary: Skip binary files.
        extensions: Only include files with these extensions.
        max_depth: Maximum directory depth (None for unlimited).

    Yields:
        Path objects for matching files.
    """

    def _walk(path: Path, depth: int) -> Iterator[Path]:
        if max_depth is not None and depth > max_depth:
            return

        try:
            entries = sorted(path.iterdir(), key=lambda p: p.name)
        except PermissionError:
            return

        for entry in entries:
            # Skip hidden unless requested
            if not include_hidden and is_hidden(entry):
                continue

            if entry.is_dir():
                # Skip ignored directories
                if should_ignore_dir(entry.name):
                    continue
                yield from _walk(entry, depth + 1)

            elif entry.is_file():
                # Skip binary if requested
                if skip_binary and is_binary_file(entry):
                    continue

                # Filter by extension if specified
                if extensions and entry.suffix.lower() not in extensions:
                    continue

                yield entry

    yield from _walk(directory, 0)


def get_file_size_human(size_bytes: int) -> str:
    """Convert file size to human-readable format.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Human-readable size string.
    """
    size: float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
