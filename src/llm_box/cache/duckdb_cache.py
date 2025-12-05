"""DuckDB-based cache implementation."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from llm_box.cache.base import Cache, CacheEntry
from llm_box.exceptions import CacheError


class DuckDBCache(Cache):
    """DuckDB-based cache for LLM responses.

    This implementation stores cached responses in a DuckDB database,
    providing fast lookups and persistent storage.

    Attributes:
        db_path: Path to the DuckDB database file.
        default_ttl: Default time-to-live for cache entries in seconds.
    """

    # SQL statements
    _CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS llm_cache (
            cache_key VARCHAR PRIMARY KEY,
            command VARCHAR NOT NULL,
            provider VARCHAR NOT NULL,
            model VARCHAR NOT NULL,
            response TEXT NOT NULL,
            tokens_used INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ttl_seconds INTEGER,
            metadata JSON
        )
    """

    _CREATE_INDEX = """
        CREATE INDEX IF NOT EXISTS idx_cache_command
        ON llm_cache(command)
    """

    _INSERT_OR_REPLACE = """
        INSERT OR REPLACE INTO llm_cache
        (cache_key, command, provider, model, response, tokens_used,
         created_at, ttl_seconds, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    _SELECT_BY_KEY = """
        SELECT cache_key, command, provider, model, response,
               tokens_used, created_at, ttl_seconds, metadata
        FROM llm_cache
        WHERE cache_key = ?
    """

    _DELETE_BY_KEY = """
        DELETE FROM llm_cache WHERE cache_key = ?
    """

    _DELETE_EXPIRED = """
        DELETE FROM llm_cache
        WHERE ttl_seconds IS NOT NULL
        AND created_at + INTERVAL (ttl_seconds) SECOND < CURRENT_TIMESTAMP
    """

    _COUNT_ALL = "SELECT COUNT(*) FROM llm_cache"

    _DELETE_ALL = "DELETE FROM llm_cache"

    _STATS_QUERY = """
        SELECT
            COUNT(*) as total_entries,
            COUNT(DISTINCT command) as unique_commands,
            COUNT(DISTINCT provider) as unique_providers,
            COUNT(DISTINCT model) as unique_models,
            SUM(tokens_used) as total_tokens,
            MIN(created_at) as oldest_entry,
            MAX(created_at) as newest_entry
        FROM llm_cache
    """

    def __init__(
        self,
        db_path: Path | str | None = None,
        default_ttl: int | None = 604800,  # 7 days
        *,
        read_only: bool = False,
    ) -> None:
        """Initialize the DuckDB cache.

        Args:
            db_path: Path to the database file. If None, uses in-memory database.
            default_ttl: Default TTL in seconds (None means no expiration).
            read_only: If True, open database in read-only mode.
        """
        self._db_path = Path(db_path) if db_path else None
        self._default_ttl = default_ttl
        self._read_only = read_only
        self._conn: duckdb.DuckDBPyConnection | None = None

        # Statistics tracking
        self._hits = 0
        self._misses = 0

        # Initialize connection and schema
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database connection and schema."""
        try:
            if self._db_path:
                # Ensure parent directory exists
                self._db_path.parent.mkdir(parents=True, exist_ok=True)
                self._conn = duckdb.connect(
                    str(self._db_path),
                    read_only=self._read_only,
                )
            else:
                # In-memory database
                self._conn = duckdb.connect(":memory:")

            # Create schema
            if not self._read_only:
                self._conn.execute(self._CREATE_TABLE)
                self._conn.execute(self._CREATE_INDEX)

        except Exception as e:
            raise CacheError(f"Failed to initialize cache database: {e}") from e

    def _ensure_connection(self) -> duckdb.DuckDBPyConnection:
        """Ensure database connection is available."""
        if self._conn is None:
            self._init_db()
        if self._conn is None:
            raise CacheError("Database connection not available")
        return self._conn

    def get(self, key: str) -> CacheEntry | None:
        """Retrieve an entry from the cache.

        Args:
            key: The cache key to look up.

        Returns:
            CacheEntry if found and not expired, None otherwise.
        """
        try:
            conn = self._ensure_connection()
            result = conn.execute(self._SELECT_BY_KEY, [key]).fetchone()

            if result is None:
                self._misses += 1
                return None

            entry = self._row_to_entry(result)

            # Check expiration
            if entry.is_expired:
                self._misses += 1
                # Clean up expired entry
                if not self._read_only:
                    conn.execute(self._DELETE_BY_KEY, [key])
                return None

            self._hits += 1
            return entry

        except Exception as e:
            raise CacheError(f"Failed to get cache entry: {e}") from e

    def set(
        self,
        key: str,
        command: str,
        provider: str,
        model: str,
        response: str,
        tokens_used: int | None = None,
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CacheEntry:
        """Store an entry in the cache.

        Args:
            key: Unique cache key.
            command: The command that generated this entry.
            provider: The LLM provider used.
            model: The model name.
            response: The response content to cache.
            tokens_used: Number of tokens used (optional).
            ttl_seconds: Time-to-live in seconds (uses default if None).
            metadata: Additional metadata (optional).

        Returns:
            The created CacheEntry.

        Raises:
            CacheError: If the cache is read-only or operation fails.
        """
        if self._read_only:
            raise CacheError("Cannot write to read-only cache")

        # Use default TTL if not specified
        if ttl_seconds is None:
            ttl_seconds = self._default_ttl

        created_at = datetime.now()
        metadata_json = json.dumps(metadata) if metadata else None

        try:
            conn = self._ensure_connection()
            conn.execute(
                self._INSERT_OR_REPLACE,
                [
                    key,
                    command,
                    provider,
                    model,
                    response,
                    tokens_used,
                    created_at,
                    ttl_seconds,
                    metadata_json,
                ],
            )

            return CacheEntry(
                key=key,
                command=command,
                provider=provider,
                model=model,
                response=response,
                tokens_used=tokens_used,
                created_at=created_at,
                ttl_seconds=ttl_seconds,
                metadata=metadata or {},
            )

        except Exception as e:
            raise CacheError(f"Failed to set cache entry: {e}") from e

    def delete(self, key: str) -> bool:
        """Delete an entry from the cache.

        Args:
            key: The cache key to delete.

        Returns:
            True if the entry was deleted, False if it didn't exist.

        Raises:
            CacheError: If the cache is read-only or operation fails.
        """
        if self._read_only:
            raise CacheError("Cannot delete from read-only cache")

        try:
            conn = self._ensure_connection()
            # Check if exists first
            exists = self.exists(key)
            if exists:
                conn.execute(self._DELETE_BY_KEY, [key])
            return exists

        except CacheError:
            raise
        except Exception as e:
            raise CacheError(f"Failed to delete cache entry: {e}") from e

    def clear(self) -> int:
        """Clear all entries from the cache.

        Returns:
            The number of entries that were cleared.

        Raises:
            CacheError: If the cache is read-only or operation fails.
        """
        if self._read_only:
            raise CacheError("Cannot clear read-only cache")

        try:
            conn = self._ensure_connection()
            count = self.count()
            conn.execute(self._DELETE_ALL)
            return count

        except CacheError:
            raise
        except Exception as e:
            raise CacheError(f"Failed to clear cache: {e}") from e

    def cleanup_expired(self) -> int:
        """Remove all expired entries from the cache.

        Returns:
            The number of entries that were removed.

        Raises:
            CacheError: If the cache is read-only or operation fails.
        """
        if self._read_only:
            raise CacheError("Cannot cleanup read-only cache")

        try:
            conn = self._ensure_connection()
            # Get count before
            count_before = self.count()
            conn.execute(self._DELETE_EXPIRED)
            # Get count after
            count_after = self.count()
            return count_before - count_after

        except CacheError:
            raise
        except Exception as e:
            raise CacheError(f"Failed to cleanup expired entries: {e}") from e

    def count(self) -> int:
        """Get the total number of entries in the cache.

        Returns:
            The number of cached entries.
        """
        try:
            conn = self._ensure_connection()
            result = conn.execute(self._COUNT_ALL).fetchone()
            return result[0] if result else 0

        except Exception as e:
            raise CacheError(f"Failed to count cache entries: {e}") from e

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics.
        """
        try:
            conn = self._ensure_connection()
            result = conn.execute(self._STATS_QUERY).fetchone()

            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

            return {
                "total_entries": result[0] if result else 0,
                "unique_commands": result[1] if result else 0,
                "unique_providers": result[2] if result else 0,
                "unique_models": result[3] if result else 0,
                "total_tokens": result[4] if result else 0,
                "oldest_entry": result[5] if result else None,
                "newest_entry": result[6] if result else None,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "db_path": str(self._db_path) if self._db_path else ":memory:",
                "default_ttl": self._default_ttl,
            }

        except Exception as e:
            raise CacheError(f"Failed to get cache stats: {e}") from e

    def _row_to_entry(self, row: tuple[Any, ...]) -> CacheEntry:
        """Convert a database row to a CacheEntry.

        Args:
            row: Tuple of (key, command, provider, model, response,
                          tokens_used, created_at, ttl_seconds, metadata).

        Returns:
            CacheEntry instance.
        """
        metadata = {}
        if row[8]:
            import contextlib

            with contextlib.suppress(json.JSONDecodeError, TypeError):
                metadata = json.loads(row[8])

        return CacheEntry(
            key=row[0],
            command=row[1],
            provider=row[2],
            model=row[3],
            response=row[4],
            tokens_used=row[5],
            created_at=row[6] if isinstance(row[6], datetime) else datetime.now(),
            ttl_seconds=row[7],
            metadata=metadata,
        )

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "DuckDBCache":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        """String representation of the cache."""
        path = str(self._db_path) if self._db_path else ":memory:"
        return f"DuckDBCache(path={path!r}, entries={self.count()})"


def get_default_cache_path() -> Path:
    """Get the default cache database path.

    Returns:
        Path to the default cache database in user's cache directory.
    """
    import os

    # Use XDG_CACHE_HOME if set, otherwise ~/.cache
    cache_home = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache_home) if cache_home else Path.home() / ".cache"

    return base / "llm-box" / "cache.duckdb"
