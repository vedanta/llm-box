"""Unit tests for the cache module."""

import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from llm_box.cache import (
    CacheEntry,
    DuckDBCache,
    generate_cache_key,
    generate_file_key,
    generate_prompt_key,
    get_default_cache_path,
    parse_cache_key,
)
from llm_box.exceptions import CacheError


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_create_cache_entry(self) -> None:
        """Test creating a cache entry."""
        entry = CacheEntry(
            key="test:key",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Test response",
        )
        assert entry.key == "test:key"
        assert entry.command == "cat"
        assert entry.provider == "ollama"
        assert entry.model == "llama3"
        assert entry.response == "Test response"
        assert entry.tokens_used is None
        assert entry.ttl_seconds is None
        assert entry.metadata == {}

    def test_cache_entry_with_all_fields(self) -> None:
        """Test cache entry with all fields populated."""
        created = datetime.now()
        entry = CacheEntry(
            key="test:key",
            command="cat",
            provider="openai",
            model="gpt-4",
            response="Response",
            tokens_used=100,
            created_at=created,
            ttl_seconds=3600,
            metadata={"extra": "data"},
        )
        assert entry.tokens_used == 100
        assert entry.created_at == created
        assert entry.ttl_seconds == 3600
        assert entry.metadata == {"extra": "data"}

    def test_is_expired_no_ttl(self) -> None:
        """Test that entry without TTL never expires."""
        entry = CacheEntry(
            key="test",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Response",
            ttl_seconds=None,
        )
        assert entry.is_expired is False

    def test_is_expired_not_yet(self) -> None:
        """Test that fresh entry is not expired."""
        entry = CacheEntry(
            key="test",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Response",
            created_at=datetime.now(),
            ttl_seconds=3600,  # 1 hour
        )
        assert entry.is_expired is False

    def test_is_expired_past_ttl(self) -> None:
        """Test that old entry is expired."""
        entry = CacheEntry(
            key="test",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Response",
            created_at=datetime.now() - timedelta(hours=2),
            ttl_seconds=3600,  # 1 hour
        )
        assert entry.is_expired is True


class TestCacheKeyGeneration:
    """Tests for cache key generation functions."""

    def test_generate_cache_key_basic(self) -> None:
        """Test basic cache key generation."""
        key = generate_cache_key("cat", "ollama", "llama3")
        assert key.startswith("cat:ollama:llama3")

    def test_generate_cache_key_with_prompt(self) -> None:
        """Test cache key with prompt."""
        key = generate_cache_key("cat", "ollama", "llama3", prompt="Explain this code")
        assert key.startswith("cat:ollama:llama3:")
        # Key should have a hash suffix
        parts = key.split(":")
        assert len(parts) == 4
        assert len(parts[3]) == 24  # 24 char hash

    def test_generate_cache_key_deterministic(self) -> None:
        """Test that same inputs produce same key."""
        key1 = generate_cache_key("cat", "ollama", "llama3", prompt="test")
        key2 = generate_cache_key("cat", "ollama", "llama3", prompt="test")
        assert key1 == key2

    def test_generate_cache_key_different_prompts(self) -> None:
        """Test that different prompts produce different keys."""
        key1 = generate_cache_key("cat", "ollama", "llama3", prompt="prompt1")
        key2 = generate_cache_key("cat", "ollama", "llama3", prompt="prompt2")
        assert key1 != key2

    def test_generate_cache_key_with_file(self, temp_dir: Path) -> None:
        """Test cache key with file path."""
        # Create a test file
        test_file = temp_dir / "test.py"
        test_file.write_text("print('hello')")

        key = generate_cache_key("cat", "ollama", "llama3", file_path=test_file)
        assert key.startswith("cat:ollama:llama3:")

    def test_generate_cache_key_file_content_change(self, temp_dir: Path) -> None:
        """Test that file content changes produce different keys."""
        test_file = temp_dir / "test.py"

        # First content
        test_file.write_text("print('hello')")
        key1 = generate_cache_key("cat", "ollama", "llama3", file_path=test_file)

        # Change content
        test_file.write_text("print('world')")
        key2 = generate_cache_key("cat", "ollama", "llama3", file_path=test_file)

        assert key1 != key2

    def test_generate_prompt_key(self) -> None:
        """Test generate_prompt_key shorthand."""
        key = generate_prompt_key("ask", "openai", "gpt-4", "What is Python?")
        assert key.startswith("ask:openai:gpt-4:")

    def test_generate_file_key(self, temp_dir: Path) -> None:
        """Test generate_file_key shorthand."""
        test_file = temp_dir / "code.py"
        test_file.write_text("def foo(): pass")

        key = generate_file_key("cat", "ollama", "llama3", test_file)
        assert key.startswith("cat:ollama:llama3:")

    def test_parse_cache_key(self) -> None:
        """Test parsing a cache key."""
        key = "cat:ollama:llama3:abc123def456"
        parsed = parse_cache_key(key)

        assert parsed["command"] == "cat"
        assert parsed["provider"] == "ollama"
        assert parsed["model"] == "llama3"
        assert parsed["hash"] == "abc123def456"

    def test_parse_cache_key_minimal(self) -> None:
        """Test parsing a minimal cache key."""
        key = "cat:ollama:llama3"
        parsed = parse_cache_key(key)

        assert parsed["command"] == "cat"
        assert parsed["provider"] == "ollama"
        assert parsed["model"] == "llama3"
        assert "hash" not in parsed


class TestDuckDBCache:
    """Tests for DuckDBCache implementation."""

    @pytest.fixture
    def memory_cache(self) -> DuckDBCache:
        """Create an in-memory cache for testing."""
        return DuckDBCache(db_path=None, default_ttl=3600)

    @pytest.fixture
    def file_cache(self, temp_dir: Path) -> DuckDBCache:
        """Create a file-based cache for testing."""
        db_path = temp_dir / "test_cache.duckdb"
        return DuckDBCache(db_path=db_path, default_ttl=3600)

    def test_create_memory_cache(self, memory_cache: DuckDBCache) -> None:
        """Test creating an in-memory cache."""
        assert memory_cache.count() == 0
        assert ":memory:" in repr(memory_cache)

    def test_create_file_cache(self, file_cache: DuckDBCache, temp_dir: Path) -> None:
        """Test creating a file-based cache."""
        assert file_cache.count() == 0
        db_path = temp_dir / "test_cache.duckdb"
        assert db_path.exists()

    def test_set_and_get(self, memory_cache: DuckDBCache) -> None:
        """Test setting and getting a cache entry."""
        entry = memory_cache.set(
            key="test:key",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Test response",
        )

        assert entry.key == "test:key"
        assert entry.response == "Test response"

        # Retrieve
        retrieved = memory_cache.get("test:key")
        assert retrieved is not None
        assert retrieved.key == "test:key"
        assert retrieved.response == "Test response"

    def test_get_nonexistent(self, memory_cache: DuckDBCache) -> None:
        """Test getting a nonexistent key."""
        result = memory_cache.get("nonexistent")
        assert result is None

    def test_set_with_tokens(self, memory_cache: DuckDBCache) -> None:
        """Test setting entry with token count."""
        entry = memory_cache.set(
            key="test:key",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Response",
            tokens_used=150,
        )
        assert entry.tokens_used == 150

        retrieved = memory_cache.get("test:key")
        assert retrieved is not None
        assert retrieved.tokens_used == 150

    def test_set_with_metadata(self, memory_cache: DuckDBCache) -> None:
        """Test setting entry with metadata."""
        metadata = {"file_path": "/path/to/file", "line_count": 100}
        memory_cache.set(
            key="test:key",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Response",
            metadata=metadata,
        )

        retrieved = memory_cache.get("test:key")
        assert retrieved is not None
        assert retrieved.metadata == metadata

    def test_set_overwrite(self, memory_cache: DuckDBCache) -> None:
        """Test that setting same key overwrites."""
        memory_cache.set(
            key="test:key",
            command="cat",
            provider="ollama",
            model="llama3",
            response="First response",
        )

        memory_cache.set(
            key="test:key",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Second response",
        )

        retrieved = memory_cache.get("test:key")
        assert retrieved is not None
        assert retrieved.response == "Second response"
        assert memory_cache.count() == 1

    def test_delete(self, memory_cache: DuckDBCache) -> None:
        """Test deleting a cache entry."""
        memory_cache.set(
            key="test:key",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Response",
        )

        assert memory_cache.delete("test:key") is True
        assert memory_cache.get("test:key") is None
        assert memory_cache.delete("test:key") is False  # Already deleted

    def test_clear(self, memory_cache: DuckDBCache) -> None:
        """Test clearing all entries."""
        # Add some entries
        for i in range(5):
            memory_cache.set(
                key=f"test:key:{i}",
                command="cat",
                provider="ollama",
                model="llama3",
                response=f"Response {i}",
            )

        assert memory_cache.count() == 5
        cleared = memory_cache.clear()
        assert cleared == 5
        assert memory_cache.count() == 0

    def test_exists(self, memory_cache: DuckDBCache) -> None:
        """Test exists method."""
        assert memory_cache.exists("test:key") is False

        memory_cache.set(
            key="test:key",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Response",
        )

        assert memory_cache.exists("test:key") is True

    def test_count(self, memory_cache: DuckDBCache) -> None:
        """Test count method."""
        assert memory_cache.count() == 0

        for i in range(3):
            memory_cache.set(
                key=f"key:{i}",
                command="cat",
                provider="ollama",
                model="llama3",
                response=f"Response {i}",
            )

        assert memory_cache.count() == 3

    def test_stats(self, memory_cache: DuckDBCache) -> None:
        """Test stats method."""
        # Add some entries
        memory_cache.set(
            key="key1",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Response 1",
            tokens_used=50,
        )
        memory_cache.set(
            key="key2",
            command="ls",
            provider="openai",
            model="gpt-4",
            response="Response 2",
            tokens_used=100,
        )

        stats = memory_cache.stats()

        assert stats["total_entries"] == 2
        assert stats["unique_commands"] == 2
        assert stats["unique_providers"] == 2
        assert stats["total_tokens"] == 150
        assert stats["db_path"] == ":memory:"

    def test_hit_miss_tracking(self, memory_cache: DuckDBCache) -> None:
        """Test hit/miss statistics tracking."""
        # Cause some misses
        memory_cache.get("nonexistent1")
        memory_cache.get("nonexistent2")

        # Add entry and cause a hit
        memory_cache.set(
            key="test:key",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Response",
        )
        memory_cache.get("test:key")

        stats = memory_cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2
        assert stats["hit_rate"] == pytest.approx(1 / 3)

    def test_ttl_expiration(self, memory_cache: DuckDBCache) -> None:
        """Test TTL-based expiration."""
        # Set with very short TTL
        memory_cache.set(
            key="test:key",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Response",
            ttl_seconds=1,  # 1 second
        )

        # Should exist immediately
        assert memory_cache.get("test:key") is not None

        # Wait for expiration
        time.sleep(1.5)

        # Should be expired
        assert memory_cache.get("test:key") is None

    def test_cleanup_expired(self) -> None:
        """Test cleanup_expired removes old entries."""
        cache = DuckDBCache(db_path=None, default_ttl=1)  # 1 second default

        # Add entries
        cache.set(
            key="short_lived",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Response",
            ttl_seconds=1,
        )
        cache.set(
            key="long_lived",
            command="cat",
            provider="ollama",
            model="llama3",
            response="Response",
            ttl_seconds=3600,
        )

        assert cache.count() == 2

        # Wait for short TTL to expire
        time.sleep(1.5)

        cleaned = cache.cleanup_expired()
        assert cleaned == 1
        assert cache.count() == 1
        assert cache.get("long_lived") is not None

    def test_context_manager(self, temp_dir: Path) -> None:
        """Test using cache as context manager."""
        db_path = temp_dir / "context_test.duckdb"

        with DuckDBCache(db_path=db_path) as cache:
            cache.set(
                key="test:key",
                command="cat",
                provider="ollama",
                model="llama3",
                response="Response",
            )
            assert cache.count() == 1

        # Reopen and verify persistence
        with DuckDBCache(db_path=db_path) as cache:
            assert cache.count() == 1
            entry = cache.get("test:key")
            assert entry is not None
            assert entry.response == "Response"

    def test_read_only_mode(self, temp_dir: Path) -> None:
        """Test read-only mode prevents writes."""
        db_path = temp_dir / "readonly_test.duckdb"

        # Create and populate cache
        with DuckDBCache(db_path=db_path) as cache:
            cache.set(
                key="test:key",
                command="cat",
                provider="ollama",
                model="llama3",
                response="Response",
            )

        # Open in read-only mode
        with DuckDBCache(db_path=db_path, read_only=True) as cache:
            # Read should work
            entry = cache.get("test:key")
            assert entry is not None

            # Write should fail
            with pytest.raises(CacheError):
                cache.set(
                    key="new:key",
                    command="cat",
                    provider="ollama",
                    model="llama3",
                    response="Response",
                )

            # Delete should fail
            with pytest.raises(CacheError):
                cache.delete("test:key")

            # Clear should fail
            with pytest.raises(CacheError):
                cache.clear()


class TestGetDefaultCachePath:
    """Tests for get_default_cache_path."""

    def test_default_path_structure(self) -> None:
        """Test that default path has expected structure."""
        path = get_default_cache_path()
        assert path.name == "cache.duckdb"
        assert path.parent.name == "llm-box"

    def test_respects_xdg_cache_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that XDG_CACHE_HOME is respected."""
        monkeypatch.setenv("XDG_CACHE_HOME", "/custom/cache")
        path = get_default_cache_path()
        assert str(path).startswith("/custom/cache")


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
