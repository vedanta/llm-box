# Search System Design

## Overview

The search system combines **semantic search** (natural language queries using embeddings) with **fuzzy matching** (approximate string matching for filenames and content). Results are ranked using a configurable weighted fusion.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Search Engine                            │
│                       (search/engine.py)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐    │
│   │   Semantic    │   │    Fuzzy      │   │   Ranking     │    │
│   │   Search      │   │   Search      │   │   Engine      │    │
│   │               │   │               │   │               │    │
│   │ • Embeddings  │   │ • Filename    │   │ • Score       │    │
│   │ • Cosine sim  │   │ • Content     │   │   fusion      │    │
│   │ • Top-K       │   │ • Levenshtein │   │ • Dedup       │    │
│   └───────┬───────┘   └───────┬───────┘   └───────┬───────┘    │
│           │                   │                   │             │
│           └───────────────────┼───────────────────┘             │
│                               │                                  │
│                     ┌─────────▼─────────┐                       │
│                     │      Indexer      │                       │
│                     │                   │                       │
│                     │ • File crawling   │                       │
│                     │ • Chunking        │                       │
│                     │ • Metadata        │                       │
│                     └─────────┬─────────┘                       │
│                               │                                  │
└───────────────────────────────┼──────────────────────────────────┘
                                │
                      ┌─────────▼─────────┐
                      │      DuckDB       │
                      │                   │
                      │ • file_index      │
                      │ • embeddings      │
                      │ • search_history  │
                      └───────────────────┘
```

## Search Modes

### 1. Semantic Search

Natural language queries that understand meaning, not just keywords.

```bash
llm-box find "authentication configuration files"
llm-box find "where is error handling done" --mode semantic
```

**How it works:**
1. Generate embedding for the query
2. Compare against stored file chunk embeddings
3. Rank by cosine similarity

### 2. Fuzzy Search

Approximate string matching for typos and partial matches.

```bash
llm-box find "confg.yml" --mode fuzzy        # Finds config.yml
llm-box find "usr auth" --mode fuzzy --type py
```

**How it works:**
1. Load file metadata from index
2. Score filename and content against query using rapidfuzz
3. Rank by fuzzy match score

### 3. Combined Search (Default)

Best of both worlds - semantic understanding with fuzzy matching.

```bash
llm-box find "auth config" --path ./src      # Uses both, ranks results
```

**How it works:**
1. Run semantic search (top 20)
2. Run fuzzy search (top 20)
3. Merge and rank using weighted fusion (60% semantic, 40% fuzzy)

## DuckDB Schema

```sql
-- File index for metadata and fuzzy search
CREATE TABLE file_index (
    id INTEGER PRIMARY KEY,
    file_path VARCHAR NOT NULL UNIQUE,
    filename VARCHAR NOT NULL,
    extension VARCHAR,
    file_hash VARCHAR NOT NULL,      -- For cache invalidation
    size_bytes INTEGER,
    modified_at TIMESTAMP,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_preview VARCHAR(1000),   -- First 1000 chars for fuzzy

    -- Metadata for filtering
    is_hidden BOOLEAN DEFAULT FALSE,
    is_binary BOOLEAN DEFAULT FALSE,
    language VARCHAR                  -- Detected programming language
);

CREATE INDEX idx_filename ON file_index(filename);
CREATE INDEX idx_extension ON file_index(extension);
CREATE INDEX idx_file_hash ON file_index(file_hash);

-- Vector embeddings for semantic search
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    file_id INTEGER REFERENCES file_index(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text VARCHAR(2000),
    embedding FLOAT[],               -- Vector embedding
    model VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(file_id, chunk_index)
);

CREATE INDEX idx_embeddings_file ON embeddings(file_id);

-- Search history for suggestions
CREATE TABLE search_history (
    id INTEGER PRIMARY KEY,
    query VARCHAR NOT NULL,
    search_type VARCHAR,             -- 'semantic', 'fuzzy', 'combined'
    result_count INTEGER,
    duration_ms INTEGER,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Implementation

### Search Engine

```python
# search/engine.py

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class SearchMode(Enum):
    SEMANTIC = "semantic"
    FUZZY = "fuzzy"
    COMBINED = "combined"


@dataclass
class SearchResult:
    file_path: str
    score: float
    match_type: str              # 'semantic', 'fuzzy', 'both'
    preview: str
    semantic_score: Optional[float] = None
    fuzzy_score: Optional[float] = None


class SearchEngine:
    def __init__(
        self,
        semantic: 'SemanticSearch',
        fuzzy: 'FuzzySearch',
        ranker: 'ResultRanker'
    ):
        self.semantic = semantic
        self.fuzzy = fuzzy
        self.ranker = ranker

    def search(
        self,
        query: str,
        path: Optional[str] = None,
        mode: SearchMode = SearchMode.COMBINED,
        top_k: int = 10,
        file_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Execute search with the specified mode."""

        if mode == SearchMode.SEMANTIC:
            results = self.semantic.search(query, path, top_k * 2)
            return self.ranker.rank_semantic(results, top_k)

        elif mode == SearchMode.FUZZY:
            results = self.fuzzy.search(query, path, top_k * 2)
            return self.ranker.rank_fuzzy(results, top_k)

        else:  # COMBINED
            semantic_results = self.semantic.search(query, path, top_k)
            fuzzy_results = self.fuzzy.search(query, path, top_k)
            return self.ranker.rank_combined(
                semantic_results,
                fuzzy_results,
                top_k
            )
```

### Semantic Search

```python
# search/semantic.py

from dataclasses import dataclass
from typing import Optional, List
import duckdb


@dataclass
class SemanticResult:
    file_path: str
    chunk_index: int
    chunk_text: str
    similarity_score: float


class SemanticSearch:
    def __init__(self, provider: 'LLMBoxProvider', db: duckdb.DuckDBPyConnection):
        self.provider = provider
        self.db = db

    def search(
        self,
        query: str,
        path: Optional[str] = None,
        top_k: int = 20,
        min_score: float = 0.5
    ) -> List[SemanticResult]:
        """Search using vector similarity."""

        # 1. Generate query embedding
        response = self.provider.embed([query])
        query_embedding = response.embeddings[0]

        # 2. Build path filter
        path_filter = ""
        params = [query_embedding]
        if path:
            path_filter = "AND f.file_path LIKE ? || '%'"
            params.append(path)

        # 3. Find similar chunks using cosine similarity
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
            SemanticResult(
                file_path=r[0],
                chunk_index=r[1],
                chunk_text=r[2],
                similarity_score=r[3]
            )
            for r in results
            if r[3] >= min_score
        ]
```

### Fuzzy Search

```python
# search/fuzzy.py

from dataclasses import dataclass
from typing import Optional, List
from rapidfuzz import fuzz
import duckdb


@dataclass
class FuzzyResult:
    file_path: str
    match_type: str      # 'filename', 'content', 'path'
    matched_text: str
    score: float         # 0-100


class FuzzySearch:
    def __init__(self, db: duckdb.DuckDBPyConnection):
        self.db = db

    def search(
        self,
        query: str,
        path: Optional[str] = None,
        top_k: int = 20,
        min_score: float = 60.0
    ) -> List[FuzzyResult]:
        """Search using fuzzy string matching."""
        results = []

        # 1. Load file metadata
        path_filter = ""
        params = []
        if path:
            path_filter = "WHERE file_path LIKE ? || '%'"
            params.append(path)

        files = self.db.execute(f"""
            SELECT file_path, filename, content_preview
            FROM file_index
            {path_filter}
            AND NOT is_binary
        """, params).fetchall()

        # 2. Score against query
        query_lower = query.lower()

        for file_path, filename, content in files:
            # Filename matching (weighted higher)
            fname_score = fuzz.partial_ratio(query_lower, filename.lower())
            if fname_score >= min_score:
                results.append(FuzzyResult(
                    file_path=file_path,
                    match_type='filename',
                    matched_text=filename,
                    score=fname_score
                ))

            # Content matching (if filename didn't match well)
            if content and fname_score < 80:
                content_score = fuzz.partial_ratio(query_lower, content.lower())
                if content_score >= min_score:
                    results.append(FuzzyResult(
                        file_path=file_path,
                        match_type='content',
                        matched_text=self._extract_context(content, query),
                        score=content_score * 0.8  # Weight content lower
                    ))

        # 3. Sort and limit
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def _extract_context(self, content: str, query: str, context: int = 50) -> str:
        """Extract snippet around the best match."""
        idx = content.lower().find(query.lower()[:3])
        if idx == -1:
            return content[:100] + "..."
        start = max(0, idx - context)
        end = min(len(content), idx + len(query) + context)
        return "..." + content[start:end] + "..."
```

### Result Ranking

```python
# search/ranking.py

from typing import List, Dict
from .engine import SearchResult
from .semantic import SemanticResult
from .fuzzy import FuzzyResult


class ResultRanker:
    def __init__(
        self,
        semantic_weight: float = 0.6,
        fuzzy_weight: float = 0.4
    ):
        self.semantic_weight = semantic_weight
        self.fuzzy_weight = fuzzy_weight

    def rank_combined(
        self,
        semantic: List[SemanticResult],
        fuzzy: List[FuzzyResult],
        top_k: int
    ) -> List[SearchResult]:
        """Merge and rank results from both search types."""

        # Build score map by file path
        scores: Dict[str, dict] = {}

        for r in semantic:
            if r.file_path not in scores:
                scores[r.file_path] = {
                    'semantic': 0,
                    'fuzzy': 0,
                    'preview': ''
                }
            scores[r.file_path]['semantic'] = max(
                scores[r.file_path]['semantic'],
                r.similarity_score
            )
            scores[r.file_path]['preview'] = r.chunk_text[:200]

        for r in fuzzy:
            if r.file_path not in scores:
                scores[r.file_path] = {
                    'semantic': 0,
                    'fuzzy': 0,
                    'preview': ''
                }
            scores[r.file_path]['fuzzy'] = max(
                scores[r.file_path]['fuzzy'],
                r.score / 100  # Normalize to 0-1
            )
            if not scores[r.file_path]['preview']:
                scores[r.file_path]['preview'] = r.matched_text

        # Compute combined score
        results = []
        for path, s in scores.items():
            combined = (
                s['semantic'] * self.semantic_weight +
                s['fuzzy'] * self.fuzzy_weight
            )

            # Determine match type
            if s['semantic'] > 0 and s['fuzzy'] > 0:
                match_type = 'both'
            elif s['semantic'] > 0:
                match_type = 'semantic'
            else:
                match_type = 'fuzzy'

            results.append(SearchResult(
                file_path=path,
                score=combined,
                match_type=match_type,
                preview=s['preview'],
                semantic_score=s['semantic'] if s['semantic'] > 0 else None,
                fuzzy_score=s['fuzzy'] if s['fuzzy'] > 0 else None
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def rank_semantic(
        self,
        results: List[SemanticResult],
        top_k: int
    ) -> List[SearchResult]:
        """Rank semantic-only results."""
        return [
            SearchResult(
                file_path=r.file_path,
                score=r.similarity_score,
                match_type='semantic',
                preview=r.chunk_text[:200],
                semantic_score=r.similarity_score
            )
            for r in results[:top_k]
        ]

    def rank_fuzzy(
        self,
        results: List[FuzzyResult],
        top_k: int
    ) -> List[SearchResult]:
        """Rank fuzzy-only results."""
        return [
            SearchResult(
                file_path=r.file_path,
                score=r.score / 100,
                match_type='fuzzy',
                preview=r.matched_text,
                fuzzy_score=r.score / 100
            )
            for r in results[:top_k]
        ]
```

### File Indexer

```python
# search/indexer.py

from pathlib import Path
from typing import Optional, List, Dict
import hashlib
import duckdb


class FileIndexer:
    def __init__(
        self,
        db: duckdb.DuckDBPyConnection,
        provider: 'LLMBoxProvider',
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        self.db = db
        self.provider = provider
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def index_directory(
        self,
        path: Path,
        extensions: Optional[List[str]] = None,
        ignore_hidden: bool = True,
        force_reindex: bool = False
    ) -> Dict[str, int]:
        """Index all files in a directory."""
        stats = {'indexed': 0, 'skipped': 0, 'errors': 0}

        for file_path in path.rglob('*'):
            if not file_path.is_file():
                continue

            # Skip hidden files
            if ignore_hidden and any(p.startswith('.') for p in file_path.parts):
                stats['skipped'] += 1
                continue

            # Filter by extension
            if extensions and file_path.suffix.lower() not in extensions:
                stats['skipped'] += 1
                continue

            try:
                if self.index_file(file_path, force_reindex):
                    stats['indexed'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                stats['errors'] += 1

        return stats

    def index_file(self, file_path: Path, force: bool = False) -> bool:
        """Index a single file. Returns True if indexed, False if skipped."""

        # Read content
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return False

        # Compute hash
        file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Check if already indexed with same hash
        existing = self.db.execute(
            "SELECT file_hash FROM file_index WHERE file_path = ?",
            [str(file_path)]
        ).fetchone()

        if existing and existing[0] == file_hash and not force:
            return False  # Already indexed

        # Upsert file metadata
        self.db.execute("""
            INSERT OR REPLACE INTO file_index
            (file_path, filename, extension, file_hash, size_bytes,
             modified_at, content_preview, is_hidden, is_binary, language)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(file_path),
            file_path.name,
            file_path.suffix,
            file_hash,
            file_path.stat().st_size,
            file_path.stat().st_mtime,
            content[:1000],
            file_path.name.startswith('.'),
            False,
            self._detect_language(file_path)
        ])

        # Get file ID
        file_id = self.db.execute(
            "SELECT id FROM file_index WHERE file_path = ?",
            [str(file_path)]
        ).fetchone()[0]

        # Generate embeddings for chunks
        if self.provider.supports_embeddings:
            chunks = self._chunk_content(content)
            if chunks:
                # Delete old embeddings
                self.db.execute(
                    "DELETE FROM embeddings WHERE file_id = ?",
                    [file_id]
                )

                # Generate and store new embeddings
                texts = [chunk for chunk, _ in chunks]
                response = self.provider.embed(texts)

                for i, ((chunk_text, _), embedding) in enumerate(
                    zip(chunks, response.embeddings)
                ):
                    self.db.execute("""
                        INSERT INTO embeddings
                        (file_id, chunk_index, chunk_text, embedding, model)
                        VALUES (?, ?, ?, ?, ?)
                    """, [file_id, i, chunk_text[:2000], embedding, response.model])

        return True

    def _chunk_content(self, content: str) -> List[tuple]:
        """Split content into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(content):
            end = min(start + self.chunk_size, len(content))
            chunk = content[start:end]
            preview = chunk[:100] + "..." if len(chunk) > 100 else chunk
            chunks.append((chunk, preview))
            start += self.chunk_size - self.chunk_overlap
        return chunks

    def _detect_language(self, file_path: Path) -> Optional[str]:
        """Detect programming language from extension."""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.rb': 'ruby',
            '.sh': 'shell',
            '.md': 'markdown',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.toml': 'toml',
        }
        return ext_map.get(file_path.suffix.lower())
```

## CLI Commands

```python
# commands/find.py

import typer
from pathlib import Path
from ..search.engine import SearchEngine, SearchMode


def find_command(
    query: str = typer.Argument(..., help="Search query"),
    path: str = typer.Option(".", "--path", "-p", help="Directory to search"),
    mode: str = typer.Option("combined", "--mode", "-m",
                              help="Search mode: semantic, fuzzy, combined"),
    top_k: int = typer.Option(10, "--top", "-n", help="Number of results"),
    index: bool = typer.Option(False, "--index", "-i",
                               help="Re-index directory before searching"),
    format: str = typer.Option("rich", "--format", "-f"),
):
    """Search for files using semantic and/or fuzzy matching."""
    ctx = get_context(...)

    # Index if requested
    if index:
        indexer = FileIndexer(ctx.db, ctx.provider)
        stats = indexer.index_directory(Path(path))
        print(f"Indexed {stats['indexed']} files")

    # Execute search
    engine = SearchEngine(...)
    results = engine.search(
        query=query,
        path=path,
        mode=SearchMode(mode),
        top_k=top_k
    )

    ctx.formatter.format_search_results(results)
```

## Output Format

```
$ llm-box find "authentication config" --path ./src

Search results for "authentication config" (combined mode)

  Score  | File                          | Match
 --------+-------------------------------+------------------------------
  0.89   | src/config/auth.py            | [semantic] OAuth2 configuration...
  0.76   | src/auth/settings.yaml        | [fuzzy] authentication: enabled...
  0.71   | src/middleware/auth_config.py | [both] JWT token configuration...
  0.65   | tests/test_auth.py            | [semantic] Test authentication...

Found 4 results in 0.23s (indexed: 127 files)
```

## Configuration

```toml
# ~/.config/llm-box/config.toml

[search]
default_mode = "combined"
top_k = 10
semantic_weight = 0.6
fuzzy_weight = 0.4
min_semantic_score = 0.5
min_fuzzy_score = 60
index_on_search = true      # Auto-index if no index exists

[search.indexer]
chunk_size = 500
chunk_overlap = 50
ignore_hidden = true
extensions = []             # Empty = all text files
```

## See Also

- [architecture.md](./architecture.md) - Overall system architecture
- [providers.md](./providers.md) - How embeddings are generated
- [caching.md](./caching.md) - DuckDB storage
