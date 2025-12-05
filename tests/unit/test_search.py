"""Tests for search functionality."""

import tempfile
from pathlib import Path

from llm_box.search import (
    FileIndexer,
    FileInfo,
    FuzzySearch,
    MatchType,
    SearchEngine,
    SearchMode,
    SemanticSearch,
    TextChunk,
)


class TestFileIndexer:
    """Tests for FileIndexer class."""

    def test_init_defaults(self) -> None:
        """Test default initialization."""
        indexer = FileIndexer()
        assert indexer.chunk_size == 500
        assert indexer.chunk_overlap == 50
        assert indexer.max_file_size == 1_000_000

    def test_init_custom(self) -> None:
        """Test custom initialization."""
        indexer = FileIndexer(
            chunk_size=1000,
            chunk_overlap=100,
            max_file_size=500_000,
        )
        assert indexer.chunk_size == 1000
        assert indexer.chunk_overlap == 100
        assert indexer.max_file_size == 500_000

    def test_chunk_content_empty(self) -> None:
        """Test chunking empty content."""
        indexer = FileIndexer()
        chunks = indexer.chunk_content("", "/path/to/file.py")
        assert chunks == []

    def test_chunk_content_small(self) -> None:
        """Test chunking small content."""
        indexer = FileIndexer(chunk_size=100)
        content = "line 1\nline 2\nline 3"
        chunks = indexer.chunk_content(content, "/path/to/file.py")

        assert len(chunks) == 1
        assert chunks[0].file_path == "/path/to/file.py"
        assert chunks[0].chunk_index == 0
        assert chunks[0].text == content

    def test_chunk_content_large(self) -> None:
        """Test chunking large content into multiple chunks."""
        indexer = FileIndexer(chunk_size=50, chunk_overlap=10)
        content = "\n".join([f"line {i}" * 5 for i in range(20)])
        chunks = indexer.chunk_content(content, "/path/to/file.py")

        assert len(chunks) > 1
        assert all(isinstance(c, TextChunk) for c in chunks)
        assert all(c.file_path == "/path/to/file.py" for c in chunks)

    def test_crawl_directory(self) -> None:
        """Test directory crawling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "test.py").write_text("print('hello')")
            Path(tmpdir, "test.txt").write_text("hello world")
            Path(tmpdir, ".hidden").write_text("hidden")

            indexer = FileIndexer()
            files = list(indexer.crawl_directory(Path(tmpdir)))

            # Should find 2 files (not hidden)
            assert len(files) == 2
            filenames = [f.filename for f in files]
            assert "test.py" in filenames
            assert "test.txt" in filenames
            assert ".hidden" not in filenames

    def test_crawl_directory_with_extension_filter(self) -> None:
        """Test directory crawling with extension filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "test.py").write_text("print('hello')")
            Path(tmpdir, "test.txt").write_text("hello world")
            Path(tmpdir, "test.js").write_text("console.log('hi')")

            indexer = FileIndexer()
            files = list(
                indexer.crawl_directory(
                    Path(tmpdir),
                    extensions=[".py"],
                )
            )

            assert len(files) == 1
            assert files[0].filename == "test.py"

    def test_get_file_metadata(self) -> None:
        """Test file metadata extraction."""
        file_info = FileInfo(
            file_path="/path/to/test.py",
            filename="test.py",
            extension=".py",
            file_hash="abc123",
            size_bytes=100,
            modified_at=None,  # type: ignore
            content_preview="print('hello')",
            is_hidden=False,
            is_binary=False,
            language="python",
            line_count=1,
        )

        indexer = FileIndexer()
        metadata = indexer.get_file_metadata(file_info)

        assert metadata["file_path"] == "/path/to/test.py"
        assert metadata["filename"] == "test.py"
        assert metadata["extension"] == ".py"
        assert metadata["language"] == "python"


class TestFuzzySearch:
    """Tests for FuzzySearch class."""

    def test_init(self) -> None:
        """Test initialization."""
        search = FuzzySearch(min_score=70, max_results=20)
        assert search.min_score == 70
        assert search.max_results == 20

    def test_search_filenames_exact(self) -> None:
        """Test fuzzy search with exact match."""
        search = FuzzySearch(min_score=50)
        files = [
            {"file_path": "/path/config.py", "filename": "config.py"},
            {"file_path": "/path/main.py", "filename": "main.py"},
            {"file_path": "/path/utils.py", "filename": "utils.py"},
        ]

        results = search.search_filenames("config", files)

        assert len(results) >= 1
        assert results[0].filename == "config.py"
        assert results[0].match_type == MatchType.FILENAME

    def test_search_filenames_fuzzy(self) -> None:
        """Test fuzzy search with approximate match."""
        search = FuzzySearch(min_score=50)
        files = [
            {"file_path": "/path/configuration.py", "filename": "configuration.py"},
            {"file_path": "/path/main.py", "filename": "main.py"},
        ]

        results = search.search_filenames("config", files)

        assert len(results) >= 1
        assert "configuration.py" in results[0].filename

    def test_search_content(self) -> None:
        """Test content search."""
        search = FuzzySearch(min_score=50)
        files = [
            {
                "file_path": "/path/auth.py",
                "filename": "auth.py",
                "content_preview": "def authenticate_user(username, password): pass",
            },
            {
                "file_path": "/path/main.py",
                "filename": "main.py",
                "content_preview": "def main(): print('hello')",
            },
        ]

        results = search.search_content("authenticate", files)

        assert len(results) >= 1
        assert results[0].filename == "auth.py"
        assert results[0].match_type == MatchType.CONTENT

    def test_search_combined(self) -> None:
        """Test combined filename and content search."""
        search = FuzzySearch(min_score=50)
        files = [
            {
                "file_path": "/path/auth.py",
                "filename": "auth.py",
                "content_preview": "authentication logic",
            },
            {
                "file_path": "/path/config.py",
                "filename": "config.py",
                "content_preview": "database config",
            },
        ]

        results = search.search_combined("auth", files)

        assert len(results) >= 1
        # Should find auth.py
        paths = [r.file_path for r in results]
        assert "/path/auth.py" in paths


class TestSemanticSearch:
    """Tests for SemanticSearch class."""

    def test_init(self) -> None:
        """Test initialization without provider."""
        search = SemanticSearch(min_score=0.6, max_results=15)
        assert search.min_score == 0.6
        assert search.max_results == 15
        assert search.provider is None

    def test_cosine_similarity_identical(self) -> None:
        """Test cosine similarity with identical vectors."""
        search = SemanticSearch()
        vec = [1.0, 2.0, 3.0]
        similarity = search.cosine_similarity(vec, vec)
        assert abs(similarity - 1.0) < 0.001

    def test_cosine_similarity_orthogonal(self) -> None:
        """Test cosine similarity with orthogonal vectors."""
        search = SemanticSearch()
        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        similarity = search.cosine_similarity(vec1, vec2)
        assert abs(similarity) < 0.001

    def test_cosine_similarity_empty(self) -> None:
        """Test cosine similarity with empty vectors."""
        search = SemanticSearch()
        similarity = search.cosine_similarity([], [])
        assert similarity == 0.0

    def test_cosine_similarity_different_lengths(self) -> None:
        """Test cosine similarity with different length vectors."""
        search = SemanticSearch()
        similarity = search.cosine_similarity([1.0, 2.0], [1.0])
        assert similarity == 0.0

    def test_embed_query_no_provider(self) -> None:
        """Test embedding without provider returns None."""
        search = SemanticSearch()
        result = search.embed_query("test query")
        assert result is None

    def test_search_with_embedding(self) -> None:
        """Test search with pre-computed embedding."""
        search = SemanticSearch(min_score=0.5)

        query_embedding = [1.0, 0.0, 0.0]
        chunks = [
            {
                "file_path": "/path/a.py",
                "filename": "a.py",
                "chunk_index": 0,
                "chunk_text": "similar content",
                "embedding": [0.9, 0.1, 0.0],  # Similar to query
            },
            {
                "file_path": "/path/b.py",
                "filename": "b.py",
                "chunk_index": 0,
                "chunk_text": "different content",
                "embedding": [0.0, 1.0, 0.0],  # Different from query
            },
        ]

        results = search.search_with_embedding(query_embedding, chunks)

        # Should find a.py with higher score
        assert len(results) >= 1
        assert results[0].file_path == "/path/a.py"


class TestSearchEngine:
    """Tests for SearchEngine class."""

    def test_init_in_memory(self) -> None:
        """Test in-memory database initialization."""
        engine = SearchEngine(db_path=None)
        assert engine.db_path is None
        engine.close()

    def test_init_with_path(self) -> None:
        """Test database initialization with path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            engine = SearchEngine(db_path=db_path)
            assert engine.db_path == db_path
            engine.close()

    def test_index_stats_empty(self) -> None:
        """Test stats on empty index."""
        engine = SearchEngine(db_path=None)
        stats = engine.get_index_stats()

        assert stats["total_files"] == 0
        assert stats["total_chunks"] == 0
        assert stats["has_embeddings"] is False

        engine.close()

    def test_clear_index(self) -> None:
        """Test clearing the index."""
        engine = SearchEngine(db_path=None)
        count = engine.clear_index()
        assert count == 0
        engine.close()

    def test_search_empty_index(self) -> None:
        """Test search on empty index."""
        engine = SearchEngine(db_path=None)
        response = engine.search(
            query="test",
            mode=SearchMode.FUZZY,
        )

        assert response.query == "test"
        assert response.mode == SearchMode.FUZZY
        assert len(response.results) == 0
        assert response.total_files_searched == 0

        engine.close()

    def test_index_directory(self) -> None:
        """Test indexing a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "test.py").write_text("print('hello')")
            Path(tmpdir, "readme.md").write_text("# Readme")

            engine = SearchEngine(db_path=None)
            stats = engine.index_directory(
                Path(tmpdir),
                generate_embeddings=False,  # Skip embeddings for speed
            )

            assert stats.files_indexed >= 2
            assert stats.errors == 0

            # Verify files are indexed
            index_stats = engine.get_index_stats()
            assert index_stats["total_files"] >= 2

            engine.close()

    def test_search_fuzzy_mode(self) -> None:
        """Test fuzzy search mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "config.py").write_text("configuration settings")
            Path(tmpdir, "main.py").write_text("main entry point")

            engine = SearchEngine(db_path=None)
            engine.index_directory(Path(tmpdir), generate_embeddings=False)

            response = engine.search(
                query="config",
                mode=SearchMode.FUZZY,
                top_k=10,
            )

            assert response.mode == SearchMode.FUZZY
            # Should find config.py
            if response.results:
                assert any("config" in r.filename for r in response.results)

            engine.close()


class TestSearchMode:
    """Tests for SearchMode enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert SearchMode.FUZZY.value == "fuzzy"
        assert SearchMode.SEMANTIC.value == "semantic"
        assert SearchMode.COMBINED.value == "combined"

    def test_from_string(self) -> None:
        """Test creating from string."""
        assert SearchMode("fuzzy") == SearchMode.FUZZY
        assert SearchMode("semantic") == SearchMode.SEMANTIC
        assert SearchMode("combined") == SearchMode.COMBINED
