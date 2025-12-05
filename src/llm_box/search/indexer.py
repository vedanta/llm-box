"""File indexer for search functionality.

This module provides functionality to crawl directories and index files
for searching, including content extraction and chunking for embeddings.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_box.utils.hashing import hash_content

# File extensions to skip (binary files)
BINARY_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    ".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a",
    ".mp4", ".avi", ".mkv", ".mov", ".webm", ".wmv",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".pyc", ".pyo", ".class", ".o", ".a", ".lib",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".db", ".sqlite", ".sqlite3", ".duckdb",
    ".pickle", ".pkl", ".npy", ".npz",
}

# Directories to skip
SKIP_DIRS = {
    ".git", ".svn", ".hg", ".bzr",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", "bower_components",
    ".venv", "venv", "env", ".env",
    ".tox", ".nox",
    "dist", "build", "*.egg-info",
    ".idea", ".vscode",
    "coverage", "htmlcov", ".coverage",
}

# Language detection by extension
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
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
    ".r": "r",
    ".R": "r",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".ps1": "powershell",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".md": "markdown",
    ".rst": "rst",
    ".txt": "text",
}


@dataclass
class FileInfo:
    """Information about an indexed file."""

    file_path: str
    filename: str
    extension: str
    file_hash: str
    size_bytes: int
    modified_at: datetime
    content_preview: str | None
    is_hidden: bool
    is_binary: bool
    language: str | None
    line_count: int | None
    content: str | None = None  # Full content for chunking


@dataclass
class TextChunk:
    """A chunk of text from a file for embedding."""

    file_path: str
    chunk_index: int
    text: str
    start_line: int | None = None
    end_line: int | None = None


@dataclass
class IndexStats:
    """Statistics from an indexing operation."""

    files_indexed: int = 0
    files_skipped: int = 0
    files_updated: int = 0
    files_unchanged: int = 0
    errors: int = 0
    total_chunks: int = 0
    error_details: list[tuple[str, str]] = field(default_factory=list)


class FileIndexer:
    """Indexes files in a directory for search.

    This class crawls directories, extracts file metadata and content,
    and prepares files for indexing in the search database.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        max_file_size: int = 1_000_000,  # 1MB
        max_preview_size: int = 2000,
    ) -> None:
        """Initialize the file indexer.

        Args:
            chunk_size: Target size for text chunks (in characters).
            chunk_overlap: Overlap between consecutive chunks.
            max_file_size: Maximum file size to index (in bytes).
            max_preview_size: Maximum size for content preview.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_file_size = max_file_size
        self.max_preview_size = max_preview_size

    def crawl_directory(
        self,
        path: Path,
        extensions: list[str] | None = None,
        ignore_hidden: bool = True,
        ignore_patterns: list[str] | None = None,
    ) -> Iterator[FileInfo]:
        """Crawl a directory and yield file information.

        Args:
            path: Directory to crawl.
            extensions: List of extensions to include (e.g., [".py", ".js"]).
                       If None, includes all non-binary files.
            ignore_hidden: Whether to ignore hidden files/directories.
            ignore_patterns: Additional patterns to ignore.

        Yields:
            FileInfo objects for each discovered file.
        """
        path = Path(path).resolve()
        if not path.is_dir():
            return

        ignore_set = SKIP_DIRS.copy()
        if ignore_patterns:
            ignore_set.update(ignore_patterns)

        for item in path.rglob("*"):
            # Skip directories
            if item.is_dir():
                continue

            # Check if any parent is in skip list
            if any(part in ignore_set for part in item.parts):
                continue

            # Check hidden files
            if ignore_hidden and any(p.startswith(".") for p in item.relative_to(path).parts):
                continue

            # Check extension filter
            if extensions and item.suffix.lower() not in extensions:
                continue

            # Skip binary files by extension
            if item.suffix.lower() in BINARY_EXTENSIONS:
                continue

            # Get file info
            try:
                file_info = self._get_file_info(item)
                if file_info:
                    yield file_info
            except (OSError, PermissionError):
                continue

    def _get_file_info(self, file_path: Path) -> FileInfo | None:
        """Extract information from a file.

        Args:
            file_path: Path to the file.

        Returns:
            FileInfo object or None if file cannot be processed.
        """
        try:
            stat = file_path.stat()
            size = stat.st_size

            # Skip files that are too large
            if size > self.max_file_size:
                return FileInfo(
                    file_path=str(file_path),
                    filename=file_path.name,
                    extension=file_path.suffix.lower(),
                    file_hash="",
                    size_bytes=size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    content_preview=None,
                    is_hidden=file_path.name.startswith("."),
                    is_binary=True,  # Treat as binary (too large)
                    language=None,
                    line_count=None,
                    content=None,
                )

            # Try to read as text
            content = self._read_file_content(file_path)
            if content is None:
                return FileInfo(
                    file_path=str(file_path),
                    filename=file_path.name,
                    extension=file_path.suffix.lower(),
                    file_hash="",
                    size_bytes=size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    content_preview=None,
                    is_hidden=file_path.name.startswith("."),
                    is_binary=True,
                    language=None,
                    line_count=None,
                    content=None,
                )

            # Calculate hash and extract info
            file_hash = hash_content(content)
            line_count = content.count("\n") + 1 if content else 0
            preview = content[:self.max_preview_size] if content else None
            language = LANGUAGE_MAP.get(file_path.suffix.lower())

            return FileInfo(
                file_path=str(file_path),
                filename=file_path.name,
                extension=file_path.suffix.lower(),
                file_hash=file_hash,
                size_bytes=size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                content_preview=preview,
                is_hidden=file_path.name.startswith("."),
                is_binary=False,
                language=language,
                line_count=line_count,
                content=content,
            )
        except Exception:
            return None

    def _read_file_content(self, file_path: Path) -> str | None:
        """Read file content as text.

        Args:
            file_path: Path to the file.

        Returns:
            File content as string, or None if unreadable.
        """
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                with open(file_path, encoding=encoding) as f:
                    content = f.read()
                    # Check for binary content (null bytes)
                    if "\x00" in content:
                        return None
                    return content
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception:
                return None

        return None

    def chunk_content(
        self,
        content: str,
        file_path: str,
    ) -> list[TextChunk]:
        """Split content into chunks for embedding.

        Args:
            content: Text content to chunk.
            file_path: Path to the source file.

        Returns:
            List of TextChunk objects.
        """
        if not content or not content.strip():
            return []

        chunks: list[TextChunk] = []
        lines = content.split("\n")
        current_chunk: list[str] = []
        current_size = 0
        chunk_start_line = 0

        for i, line in enumerate(lines):
            line_size = len(line) + 1  # +1 for newline

            # Check if adding this line exceeds chunk size
            if current_size + line_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = "\n".join(current_chunk)
                chunks.append(TextChunk(
                    file_path=file_path,
                    chunk_index=len(chunks),
                    text=chunk_text,
                    start_line=chunk_start_line,
                    end_line=i - 1,
                ))

                # Start new chunk with overlap
                overlap_lines = self._get_overlap_lines(current_chunk)
                current_chunk = overlap_lines + [line]
                current_size = sum(len(ln) + 1 for ln in current_chunk)
                chunk_start_line = max(0, i - len(overlap_lines))
            else:
                current_chunk.append(line)
                current_size += line_size

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(TextChunk(
                file_path=file_path,
                chunk_index=len(chunks),
                text=chunk_text,
                start_line=chunk_start_line,
                end_line=len(lines) - 1,
            ))

        return chunks

    def _get_overlap_lines(self, lines: list[str]) -> list[str]:
        """Get lines to include as overlap in next chunk.

        Args:
            lines: Lines from the current chunk.

        Returns:
            Lines to include as overlap.
        """
        if not lines:
            return []

        overlap_size = 0
        overlap_lines: list[str] = []

        for line in reversed(lines):
            line_size = len(line) + 1
            if overlap_size + line_size > self.chunk_overlap:
                break
            overlap_lines.insert(0, line)
            overlap_size += line_size

        return overlap_lines

    def get_file_metadata(self, file_info: FileInfo) -> dict[str, Any]:
        """Convert FileInfo to a dictionary for database storage.

        Args:
            file_info: FileInfo object.

        Returns:
            Dictionary of file metadata.
        """
        return {
            "file_path": file_info.file_path,
            "filename": file_info.filename,
            "extension": file_info.extension,
            "file_hash": file_info.file_hash,
            "size_bytes": file_info.size_bytes,
            "modified_at": file_info.modified_at,
            "content_preview": file_info.content_preview,
            "is_hidden": file_info.is_hidden,
            "is_binary": file_info.is_binary,
            "language": file_info.language,
            "line_count": file_info.line_count,
        }
