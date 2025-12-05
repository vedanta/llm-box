"""Unified search engine.

This module provides a unified search interface that combines
fuzzy and semantic search with result ranking and fusion.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import duckdb

from llm_box.providers.base import LLMBoxProvider
from llm_box.search.fuzzy import FuzzySearch
from llm_box.search.indexer import FileIndexer, FileInfo, IndexStats
from llm_box.search.schema import (
    ALL_INDEXES,
    ALL_TABLES,
)
from llm_box.search.semantic import SemanticSearch


class SearchMode(str, Enum):
    """Search mode selection."""

    FUZZY = "fuzzy"
    SEMANTIC = "semantic"
    COMBINED = "combined"


@dataclass
class SearchResult:
    """Unified search result."""

    file_path: str
    filename: str
    score: float  # 0-1 normalized
    match_type: str  # 'fuzzy', 'semantic', 'combined'
    preview: str
    language: str | None = None
    line_number: int | None = None
    fuzzy_score: float | None = None
    semantic_score: float | None = None


@dataclass
class SearchResponse:
    """Response from a search operation."""

    query: str
    mode: SearchMode
    results: list[SearchResult]
    total_files_searched: int
    search_time_ms: float
    indexed: bool = False


class SearchEngine:
    """Unified search engine combining fuzzy and semantic search.

    This engine provides a single interface for searching files
    using multiple strategies with intelligent result fusion.
    """

    def __init__(
        self,
        db_path: Path | str | None = None,
        provider: LLMBoxProvider | None = None,
        fuzzy_weight: float = 0.4,
        semantic_weight: float = 0.6,
    ) -> None:
        """Initialize the search engine.

        Args:
            db_path: Path to DuckDB database. None for in-memory.
            provider: LLM provider for semantic search.
            fuzzy_weight: Weight for fuzzy search in combined mode.
            semantic_weight: Weight for semantic search in combined mode.
        """
        self.db_path = Path(db_path) if db_path else None
        self.provider = provider
        self.fuzzy_weight = fuzzy_weight
        self.semantic_weight = semantic_weight

        # Initialize components
        self.indexer = FileIndexer()
        self.fuzzy = FuzzySearch()
        self.semantic = SemanticSearch(provider=provider)

        # Initialize database connection
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the database schema."""
        conn = self._get_connection()

        # Create tables
        for table_sql in ALL_TABLES:
            conn.execute(table_sql)

        # Create indexes
        for index_sql in ALL_INDEXES:
            conn.execute(index_sql)

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get or create database connection."""
        if self._conn is None:
            if self.db_path:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                self._conn = duckdb.connect(str(self.db_path))
            else:
                self._conn = duckdb.connect(":memory:")
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def set_provider(self, provider: LLMBoxProvider) -> None:
        """Set the LLM provider for semantic search.

        Args:
            provider: LLM provider with embedding support.
        """
        self.provider = provider
        self.semantic.set_provider(provider)

    # -------------------------------------------------------------------------
    # Indexing Operations
    # -------------------------------------------------------------------------

    def index_directory(
        self,
        path: Path | str,
        extensions: list[str] | None = None,
        force_reindex: bool = False,
        generate_embeddings: bool = True,
    ) -> IndexStats:
        """Index all files in a directory.

        Args:
            path: Directory to index.
            extensions: File extensions to include.
            force_reindex: Re-index files even if unchanged.
            generate_embeddings: Generate embeddings for semantic search.

        Returns:
            IndexStats with indexing results.
        """
        path = Path(path).resolve()
        stats = IndexStats()
        conn = self._get_connection()

        # Crawl and index files
        for file_info in self.indexer.crawl_directory(
            path,
            extensions=extensions,
            ignore_hidden=True,
        ):
            try:
                result = self._index_file(
                    conn, file_info, force_reindex, generate_embeddings
                )
                if result == "indexed":
                    stats.files_indexed += 1
                elif result == "updated":
                    stats.files_updated += 1
                elif result == "unchanged":
                    stats.files_unchanged += 1
                elif result == "skipped":
                    stats.files_skipped += 1
            except Exception as e:
                stats.errors += 1
                stats.error_details.append((file_info.file_path, str(e)))

        return stats

    def index_file(
        self,
        file_path: Path | str,
        force_reindex: bool = False,
        generate_embeddings: bool = True,
    ) -> bool:
        """Index a single file.

        Args:
            file_path: Path to the file.
            force_reindex: Re-index even if unchanged.
            generate_embeddings: Generate embeddings for semantic search.

        Returns:
            True if file was indexed, False otherwise.
        """
        file_path = Path(file_path).resolve()
        conn = self._get_connection()

        # Get file info
        file_info = self.indexer._get_file_info(file_path)
        if not file_info or file_info.is_binary:
            return False

        result = self._index_file(conn, file_info, force_reindex, generate_embeddings)
        return result in ("indexed", "updated")

    def _index_file(
        self,
        conn: duckdb.DuckDBPyConnection,
        file_info: FileInfo,
        force_reindex: bool,
        generate_embeddings: bool,
    ) -> str:
        """Internal method to index a file.

        Returns:
            'indexed', 'updated', 'unchanged', or 'skipped'
        """
        if file_info.is_binary or not file_info.content:
            return "skipped"

        # Check if file exists and is unchanged
        existing = conn.execute(
            "SELECT id, file_hash FROM file_index WHERE file_path = ?",
            [file_info.file_path],
        ).fetchone()

        if existing and not force_reindex and existing[1] == file_info.file_hash:
            return "unchanged"

        # Insert or update file index
        if existing:
            file_id = existing[0]
            conn.execute(
                """
                UPDATE file_index SET
                    filename = ?, extension = ?, file_hash = ?,
                    size_bytes = ?, modified_at = ?, indexed_at = ?,
                    content_preview = ?, is_hidden = ?, is_binary = ?,
                    language = ?, line_count = ?
                WHERE id = ?
            """,
                [
                    file_info.filename,
                    file_info.extension,
                    file_info.file_hash,
                    file_info.size_bytes,
                    file_info.modified_at,
                    datetime.now(),
                    file_info.content_preview,
                    file_info.is_hidden,
                    file_info.is_binary,
                    file_info.language,
                    file_info.line_count,
                    file_id,
                ],
            )
            result = "updated"
        else:
            conn.execute(
                """
                INSERT INTO file_index
                (file_path, filename, extension, file_hash, size_bytes,
                 modified_at, indexed_at, content_preview, is_hidden,
                 is_binary, language, line_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    file_info.file_path,
                    file_info.filename,
                    file_info.extension,
                    file_info.file_hash,
                    file_info.size_bytes,
                    file_info.modified_at,
                    datetime.now(),
                    file_info.content_preview,
                    file_info.is_hidden,
                    file_info.is_binary,
                    file_info.language,
                    file_info.line_count,
                ],
            )
            row = conn.execute(
                "SELECT id FROM file_index WHERE file_path = ?", [file_info.file_path]
            ).fetchone()
            file_id = row[0] if row else 0
            result = "indexed"

        # Generate and store embeddings
        if generate_embeddings and self.provider and file_info.content:
            self._generate_embeddings(conn, file_id, file_info)

        return result

    def _generate_embeddings(
        self,
        conn: duckdb.DuckDBPyConnection,
        file_id: int,
        file_info: FileInfo,
    ) -> int:
        """Generate and store embeddings for a file.

        Returns:
            Number of chunks embedded.
        """
        if not file_info.content:
            return 0

        # Chunk the content
        chunks = self.indexer.chunk_content(
            file_info.content,
            file_info.file_path,
        )

        if not chunks:
            return 0

        # Generate embeddings
        texts = [chunk.text for chunk in chunks]
        embeddings = self.semantic.embed_texts(texts)

        if not embeddings or len(embeddings) != len(chunks):
            return 0

        # Delete old embeddings
        conn.execute("DELETE FROM embeddings WHERE file_id = ?", [file_id])

        # Insert new embeddings
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            conn.execute(
                """
                INSERT INTO embeddings
                (file_id, chunk_index, chunk_text, embedding, model)
                VALUES (?, ?, ?, ?, ?)
            """,
                [
                    file_id,
                    chunk.chunk_index,
                    chunk.text[:2000],
                    embedding,
                    self.provider.model_name if self.provider else "unknown",
                ],
            )

        return len(chunks)

    # -------------------------------------------------------------------------
    # Search Operations
    # -------------------------------------------------------------------------

    def search(
        self,
        query: str,
        path: Path | str | None = None,
        mode: SearchMode = SearchMode.COMBINED,
        top_k: int = 10,
        extensions: list[str] | None = None,
    ) -> SearchResponse:
        """Search for files matching a query.

        Args:
            query: Search query (natural language or fuzzy pattern).
            path: Optional path filter (only search within this path).
            mode: Search mode (fuzzy, semantic, or combined).
            top_k: Maximum number of results.
            extensions: Filter by file extensions.

        Returns:
            SearchResponse with results.
        """
        import time

        start_time = time.time()

        conn = self._get_connection()

        # Get files from index
        files = self._get_indexed_files(conn, path, extensions)
        total_files = len(files)

        results: list[SearchResult] = []

        if mode == SearchMode.FUZZY:
            results = self._search_fuzzy(query, files, top_k)
        elif mode == SearchMode.SEMANTIC:
            results = self._search_semantic(query, conn, path, extensions, top_k)
        else:  # COMBINED
            results = self._search_combined(query, files, conn, path, extensions, top_k)

        search_time = (time.time() - start_time) * 1000

        # Record search history
        self._record_search(conn, query, mode.value, len(results))

        return SearchResponse(
            query=query,
            mode=mode,
            results=results,
            total_files_searched=total_files,
            search_time_ms=search_time,
        )

    def _get_indexed_files(
        self,
        conn: duckdb.DuckDBPyConnection,
        path: Path | str | None = None,
        extensions: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get indexed files from database.

        Returns:
            List of file records.
        """
        query = """
            SELECT file_path, filename, extension, content_preview,
                   language, line_count
            FROM file_index
            WHERE is_binary = FALSE
        """
        params: list[Any] = []

        if path:
            path_str = str(Path(path).resolve())
            query += " AND file_path LIKE ?"
            params.append(f"{path_str}%")

        if extensions:
            placeholders = ",".join("?" for _ in extensions)
            query += f" AND extension IN ({placeholders})"
            params.extend(extensions)

        rows = conn.execute(query, params).fetchall()

        return [
            {
                "file_path": row[0],
                "filename": row[1],
                "extension": row[2],
                "content_preview": row[3],
                "language": row[4],
                "line_count": row[5],
            }
            for row in rows
        ]

    def _search_fuzzy(
        self,
        query: str,
        files: list[dict[str, Any]],
        top_k: int,
    ) -> list[SearchResult]:
        """Perform fuzzy search.

        Returns:
            List of SearchResult objects.
        """
        fuzzy_results = self.fuzzy.search_combined(query, files)

        results = []
        for fr in fuzzy_results[:top_k]:
            # Find file info
            file_info = next((f for f in files if f["file_path"] == fr.file_path), {})

            results.append(
                SearchResult(
                    file_path=fr.file_path,
                    filename=fr.filename,
                    score=fr.score / 100.0,  # Normalize to 0-1
                    match_type="fuzzy",
                    preview=fr.context or fr.matched_text,
                    language=file_info.get("language"),
                    fuzzy_score=fr.score / 100.0,
                )
            )

        return results

    def _search_semantic(
        self,
        query: str,
        conn: duckdb.DuckDBPyConnection,
        path: Path | str | None,
        extensions: list[str] | None,
        top_k: int,
    ) -> list[SearchResult]:
        """Perform semantic search.

        Returns:
            List of SearchResult objects.
        """
        if not self.provider:
            return []

        # Get chunks with embeddings
        chunks = self._get_indexed_chunks(conn, path, extensions)
        if not chunks:
            return []

        semantic_results = self.semantic.search_files(query, chunks)

        results = []
        for sr in semantic_results[:top_k]:
            results.append(
                SearchResult(
                    file_path=sr.file_path,
                    filename=sr.filename,
                    score=sr.similarity_score,
                    match_type="semantic",
                    preview=sr.chunk_text[:200] if sr.chunk_text else "",
                    line_number=sr.start_line,
                    semantic_score=sr.similarity_score,
                )
            )

        return results

    def _search_combined(
        self,
        query: str,
        files: list[dict[str, Any]],
        conn: duckdb.DuckDBPyConnection,
        path: Path | str | None,
        extensions: list[str] | None,
        top_k: int,
    ) -> list[SearchResult]:
        """Perform combined fuzzy + semantic search.

        Returns:
            List of SearchResult objects with fused scores.
        """
        # Get both result sets
        fuzzy_results = self._search_fuzzy(query, files, top_k * 2)
        semantic_results = self._search_semantic(
            query, conn, path, extensions, top_k * 2
        )

        # Build score map by file
        scores: dict[str, dict[str, Any]] = {}

        for fr in fuzzy_results:
            path_key = fr.file_path
            if path_key not in scores:
                scores[path_key] = {
                    "filename": fr.filename,
                    "fuzzy": 0.0,
                    "semantic": 0.0,
                    "preview": "",
                    "language": fr.language,
                    "line_number": None,
                }
            scores[path_key]["fuzzy"] = max(scores[path_key]["fuzzy"], fr.score)
            if not scores[path_key]["preview"]:
                scores[path_key]["preview"] = fr.preview

        for sr in semantic_results:
            path_key = sr.file_path
            if path_key not in scores:
                scores[path_key] = {
                    "filename": sr.filename,
                    "fuzzy": 0.0,
                    "semantic": 0.0,
                    "preview": "",
                    "language": None,
                    "line_number": None,
                }
            scores[path_key]["semantic"] = max(scores[path_key]["semantic"], sr.score)
            if not scores[path_key]["preview"]:
                scores[path_key]["preview"] = sr.preview
            if sr.line_number:
                scores[path_key]["line_number"] = sr.line_number

        # Compute combined scores
        results = []
        for path_key, data in scores.items():
            combined_score = (
                data["fuzzy"] * self.fuzzy_weight
                + data["semantic"] * self.semantic_weight
            )

            results.append(
                SearchResult(
                    file_path=path_key,
                    filename=data["filename"],
                    score=combined_score,
                    match_type="combined",
                    preview=data["preview"],
                    language=data["language"],
                    line_number=data["line_number"],
                    fuzzy_score=data["fuzzy"] if data["fuzzy"] > 0 else None,
                    semantic_score=data["semantic"] if data["semantic"] > 0 else None,
                )
            )

        # Sort by combined score
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def _get_indexed_chunks(
        self,
        conn: duckdb.DuckDBPyConnection,
        path: Path | str | None = None,
        extensions: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get indexed chunks with embeddings from database.

        Returns:
            List of chunk records.
        """
        query = """
            SELECT f.file_path, f.filename, e.chunk_index, e.chunk_text,
                   e.embedding, f.language
            FROM embeddings e
            JOIN file_index f ON e.file_id = f.id
            WHERE e.embedding IS NOT NULL
        """
        params: list[Any] = []

        if path:
            path_str = str(Path(path).resolve())
            query += " AND f.file_path LIKE ?"
            params.append(f"{path_str}%")

        if extensions:
            placeholders = ",".join("?" for _ in extensions)
            query += f" AND f.extension IN ({placeholders})"
            params.extend(extensions)

        rows = conn.execute(query, params).fetchall()

        return [
            {
                "file_path": row[0],
                "filename": row[1],
                "chunk_index": row[2],
                "chunk_text": row[3],
                "embedding": row[4],
                "language": row[5],
            }
            for row in rows
        ]

    def _record_search(
        self,
        conn: duckdb.DuckDBPyConnection,
        query: str,
        search_type: str,
        result_count: int,
    ) -> None:
        """Record search in history."""
        import contextlib

        with contextlib.suppress(Exception):
            conn.execute(
                """
                INSERT INTO search_history (query, search_type, result_count)
                VALUES (?, ?, ?)
            """,
                [query, search_type, result_count],
            )

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def get_index_stats(self) -> dict[str, Any]:
        """Get statistics about the search index.

        Returns:
            Dictionary of statistics.
        """
        conn = self._get_connection()

        file_row = conn.execute("SELECT COUNT(*) FROM file_index").fetchone()
        file_count: int = file_row[0] if file_row else 0

        chunk_row = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()
        chunk_count: int = chunk_row[0] if chunk_row else 0

        languages = conn.execute("""
            SELECT language, COUNT(*) as count
            FROM file_index
            WHERE language IS NOT NULL
            GROUP BY language
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()

        return {
            "total_files": file_count,
            "total_chunks": chunk_count,
            "languages": {row[0]: row[1] for row in languages},
            "has_embeddings": chunk_count > 0,
        }

    def clear_index(self) -> int:
        """Clear the search index.

        Returns:
            Number of files removed.
        """
        conn = self._get_connection()

        count_row = conn.execute("SELECT COUNT(*) FROM file_index").fetchone()
        count: int = count_row[0] if count_row else 0

        conn.execute("DELETE FROM embeddings")
        conn.execute("DELETE FROM file_index")
        conn.execute("DELETE FROM search_history")

        return count
