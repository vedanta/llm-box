# Caching Design

## Overview

llm-box uses DuckDB as a unified storage layer for:
1. **LLM response caching** - Avoid redundant API calls
2. **Vector embeddings** - Store file embeddings for semantic search
3. **File metadata** - Index for fuzzy search and cache invalidation

## Why DuckDB?

- **Embedded**: No server setup, single file database
- **Fast analytics**: Columnar storage optimized for aggregations
- **Array support**: Native operations for vector embeddings
- **SQL interface**: Familiar query language
- **Zero dependencies**: Pure C++ with Python bindings

## Database Location

```
~/.cache/llm-box/
└── cache.duckdb          # Single database file
```

Override with environment variable: `LLMBOX_CACHE_PATH`

## Schema

### LLM Response Cache

```sql
CREATE TABLE llm_cache (
    id INTEGER PRIMARY KEY,
    cache_key VARCHAR NOT NULL UNIQUE,
    command VARCHAR NOT NULL,          -- 'ls', 'cat', 'find', etc.
    provider VARCHAR NOT NULL,         -- 'ollama', 'openai', 'anthropic'
    model VARCHAR NOT NULL,
    prompt_hash VARCHAR NOT NULL,      -- SHA256 of prompt
    response TEXT NOT NULL,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 1,
    ttl_seconds INTEGER,
    metadata JSON
);

CREATE INDEX idx_cache_key ON llm_cache(cache_key);
CREATE INDEX idx_command ON llm_cache(command);
CREATE INDEX idx_created_at ON llm_cache(created_at);
```

### File Index (for search)

```sql
CREATE TABLE file_index (
    id INTEGER PRIMARY KEY,
    file_path VARCHAR NOT NULL UNIQUE,
    filename VARCHAR NOT NULL,
    extension VARCHAR,
    file_hash VARCHAR NOT NULL,        -- SHA256 of content (16 chars)
    size_bytes INTEGER,
    modified_at TIMESTAMP,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_preview VARCHAR(1000),
    is_hidden BOOLEAN DEFAULT FALSE,
    is_binary BOOLEAN DEFAULT FALSE,
    language VARCHAR
);

CREATE INDEX idx_file_path ON file_index(file_path);
CREATE INDEX idx_filename ON file_index(filename);
CREATE INDEX idx_extension ON file_index(extension);
CREATE INDEX idx_file_hash ON file_index(file_hash);
```

### Vector Embeddings

```sql
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    file_id INTEGER REFERENCES file_index(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text VARCHAR(2000),
    embedding FLOAT[],                 -- Vector array
    model VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(file_id, chunk_index)
);

CREATE INDEX idx_embeddings_file ON embeddings(file_id);
```

### Search History

```sql
CREATE TABLE search_history (
    id INTEGER PRIMARY KEY,
    query VARCHAR NOT NULL,
    search_type VARCHAR,               -- 'semantic', 'fuzzy', 'combined'
    result_count INTEGER,
    duration_ms INTEGER,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_search_history_query ON search_history(query);
```

## Cache Implementation

```python
# cache/duckdb_cache.py

from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import duckdb
import json


class DuckDBCache:
    """DuckDB-based cache for LLM responses."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        default_ttl: int = 604800  # 7 days
    ):
        if db_path is None:
            db_path = Path.home() / ".cache" / "llm-box" / "cache.duckdb"

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.default_ttl = default_ttl
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._init_schema()

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path))
        return self._conn

    def _init_schema(self):
        """Initialize database schema."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                id INTEGER PRIMARY KEY,
                cache_key VARCHAR NOT NULL UNIQUE,
                command VARCHAR NOT NULL,
                provider VARCHAR NOT NULL,
                model VARCHAR NOT NULL,
                prompt_hash VARCHAR NOT NULL,
                response TEXT NOT NULL,
                tokens_used INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1,
                ttl_seconds INTEGER,
                metadata JSON
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_key ON llm_cache(cache_key)
        """)

    def get(self, key: str) -> Optional[str]:
        """Retrieve cached response."""
        result = self.conn.execute("""
            SELECT response, created_at, ttl_seconds
            FROM llm_cache
            WHERE cache_key = ?
        """, [key]).fetchone()

        if result is None:
            return None

        response, created_at, ttl = result

        # Check TTL
        if ttl is not None:
            expiry = created_at + timedelta(seconds=ttl)
            if datetime.now() > expiry:
                self.delete(key)
                return None

        # Update access stats
        self.conn.execute("""
            UPDATE llm_cache
            SET last_accessed_at = CURRENT_TIMESTAMP,
                access_count = access_count + 1
            WHERE cache_key = ?
        """, [key])

        return response

    def set(
        self,
        key: str,
        value: str,
        command: str = "unknown",
        provider: str = "unknown",
        model: str = "unknown",
        prompt_hash: str = "",
        tokens_used: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store response in cache."""
        ttl = ttl_seconds or self.default_ttl
        meta_json = json.dumps(metadata) if metadata else None

        self.conn.execute("""
            INSERT OR REPLACE INTO llm_cache
            (cache_key, command, provider, model, prompt_hash,
             response, tokens_used, ttl_seconds, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [key, command, provider, model, prompt_hash,
              value, tokens_used, ttl, meta_json])

    def delete(self, key: str) -> bool:
        """Delete a cache entry."""
        result = self.conn.execute(
            "DELETE FROM llm_cache WHERE cache_key = ? RETURNING id",
            [key]
        ).fetchone()
        return result is not None

    def clear(self, command: Optional[str] = None) -> int:
        """Clear cache entries."""
        if command:
            result = self.conn.execute(
                "DELETE FROM llm_cache WHERE command = ?",
                [command]
            )
        else:
            result = self.conn.execute("DELETE FROM llm_cache")
        return result.rowcount

    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        result = self.conn.execute("""
            DELETE FROM llm_cache
            WHERE ttl_seconds IS NOT NULL
            AND created_at + INTERVAL (ttl_seconds) SECOND < CURRENT_TIMESTAMP
        """)
        return result.rowcount

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.conn.execute(
            "SELECT COUNT(*) FROM llm_cache"
        ).fetchone()[0]

        by_command = dict(self.conn.execute("""
            SELECT command, COUNT(*) as count
            FROM llm_cache
            GROUP BY command
        """).fetchall())

        by_provider = dict(self.conn.execute("""
            SELECT provider, COUNT(*) as count
            FROM llm_cache
            GROUP BY provider
        """).fetchall())

        oldest = self.conn.execute(
            "SELECT MIN(created_at) FROM llm_cache"
        ).fetchone()[0]

        size = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "total_entries": total,
            "by_command": by_command,
            "by_provider": by_provider,
            "oldest_entry": oldest,
            "db_size_bytes": size,
            "db_path": str(self.db_path)
        }
```

## Cache Key Generation

```python
# cache/keys.py

import hashlib
import json
from typing import Any


def build_cache_key(command: str, **kwargs) -> str:
    """Build a deterministic cache key from command and parameters."""
    # Sort kwargs for deterministic ordering
    sorted_kwargs = sorted(kwargs.items())

    # Create a unique string representation
    key_data = {
        "command": command,
        "params": dict(sorted_kwargs)
    }

    key_string = json.dumps(key_data, sort_keys=True)

    # Hash for fixed-length key
    hash_digest = hashlib.sha256(key_string.encode()).hexdigest()[:32]

    return f"{command}:{hash_digest}"


def hash_prompt(prompt: str) -> str:
    """Hash a prompt for cache lookup."""
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


def hash_file_content(content: str) -> str:
    """Hash file content for cache invalidation."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

## Cache Invalidation

### Strategies

1. **TTL-based**: Entries expire after configured time (default: 7 days)
2. **Content-based**: File hash changes trigger re-indexing
3. **Manual**: `llm-box cache clear` command

### Content Hash Invalidation

```python
def is_cache_valid(file_path: Path, cached_hash: str) -> bool:
    """Check if cached data is still valid for a file."""
    content = file_path.read_text()
    current_hash = hash_file_content(content)
    return current_hash == cached_hash
```

## Vector Store

```python
# cache/vector_store.py

from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
import duckdb


@dataclass
class VectorSearchResult:
    file_path: str
    chunk_index: int
    content_preview: str
    similarity_score: float


class VectorStore:
    """Vector storage for semantic file search."""

    def __init__(self, db: duckdb.DuckDBPyConnection):
        self.db = db

    def store_embeddings(
        self,
        file_id: int,
        chunks: List[str],
        embeddings: List[List[float]],
        model: str
    ) -> None:
        """Store embeddings for a file."""
        # Delete existing embeddings
        self.db.execute(
            "DELETE FROM embeddings WHERE file_id = ?",
            [file_id]
        )

        # Insert new embeddings
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            self.db.execute("""
                INSERT INTO embeddings
                (file_id, chunk_index, chunk_text, embedding, model)
                VALUES (?, ?, ?, ?, ?)
            """, [file_id, i, chunk[:2000], embedding, model])

    def search(
        self,
        query_embedding: List[float],
        path: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.5
    ) -> List[VectorSearchResult]:
        """Search for similar vectors."""
        path_filter = ""
        params = [query_embedding]

        if path:
            path_filter = "AND f.file_path LIKE ? || '%'"
            params.append(path)

        results = self.db.execute(f"""
            SELECT
                f.file_path,
                e.chunk_index,
                e.chunk_text,
                list_cosine_similarity(e.embedding, ?) as score
            FROM embeddings e
            JOIN file_index f ON e.file_id = f.id
            WHERE e.embedding IS NOT NULL
            {path_filter}
            ORDER BY score DESC
            LIMIT ?
        """, params + [top_k]).fetchall()

        return [
            VectorSearchResult(
                file_path=r[0],
                chunk_index=r[1],
                content_preview=r[2][:200] if r[2] else "",
                similarity_score=r[3]
            )
            for r in results
            if r[3] >= min_score
        ]

    def delete_file_embeddings(self, file_id: int) -> int:
        """Delete embeddings for a file."""
        result = self.db.execute(
            "DELETE FROM embeddings WHERE file_id = ?",
            [file_id]
        )
        return result.rowcount
```

## CLI Commands

```bash
# View cache statistics
$ llm-box cache stats
Cache Statistics:
  Total entries: 1,234
  Database size: 45.2 MB

  By command:
    ls:   456
    cat:  312
    find: 466

  By provider:
    ollama:    890
    openai:    344

# Clear all cache
$ llm-box cache clear
Cleared 1,234 cache entries

# Clear specific command cache
$ llm-box cache clear --command ls
Cleared 456 cache entries for 'ls'

# Cleanup expired entries
$ llm-box cache cleanup
Removed 123 expired entries
```

## Configuration

```toml
# ~/.config/llm-box/config.toml

[cache]
enabled = true
path = "~/.cache/llm-box/cache.duckdb"
default_ttl_seconds = 604800  # 7 days
max_size_mb = 500
cleanup_on_start = true

[cache.commands]
# Per-command TTL overrides
ls = 86400      # 1 day
cat = 604800    # 7 days
find = 3600     # 1 hour (search results change often)
```

## Performance

### Benchmarks (typical)

| Operation | Time |
|-----------|------|
| Cache lookup (hit) | ~0.5ms |
| Cache write | ~2ms |
| Vector search (1000 embeddings) | ~10ms |
| Vector search (10000 embeddings) | ~50ms |

### Optimization Tips

1. **Vacuum periodically**: `VACUUM` to reclaim space
2. **Index tuning**: Add indexes for frequent query patterns
3. **Batch writes**: Group multiple inserts in transactions
4. **Connection pooling**: Reuse connections across commands

## See Also

- [architecture.md](./architecture.md) - Overall system architecture
- [search.md](./search.md) - How cache is used for search
- [providers.md](./providers.md) - What gets cached
