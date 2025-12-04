"""Tests for hashing utilities."""

from pathlib import Path

import pytest

from llm_box.utils.hashing import (
    hash_content,
    hash_file,
    hash_file_metadata,
    hash_for_cache,
    hash_prompt,
)


class TestHashContent:
    """Tests for content hashing."""

    def test_hash_content_deterministic(self) -> None:
        """Test that same content produces same hash."""
        content = "Hello, World!"
        hash1 = hash_content(content)
        hash2 = hash_content(content)
        assert hash1 == hash2

    def test_hash_content_different_input(self) -> None:
        """Test that different content produces different hash."""
        hash1 = hash_content("Hello")
        hash2 = hash_content("World")
        assert hash1 != hash2

    def test_hash_content_length(self) -> None:
        """Test hash length parameter."""
        content = "test"
        assert len(hash_content(content, length=8)) == 8
        assert len(hash_content(content, length=32)) == 32
        assert len(hash_content(content, length=64)) == 64


class TestHashFile:
    """Tests for file hashing."""

    def test_hash_file(self, temp_dir: Path) -> None:
        """Test hashing a file."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("Test content")

        file_hash = hash_file(file_path)
        assert len(file_hash) == 16

    def test_hash_file_deterministic(self, temp_dir: Path) -> None:
        """Test that same file produces same hash."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("Test content")

        hash1 = hash_file(file_path)
        hash2 = hash_file(file_path)
        assert hash1 == hash2

    def test_hash_file_changes_with_content(self, temp_dir: Path) -> None:
        """Test that hash changes when content changes."""
        file_path = temp_dir / "test.txt"

        file_path.write_text("Content 1")
        hash1 = hash_file(file_path)

        file_path.write_text("Content 2")
        hash2 = hash_file(file_path)

        assert hash1 != hash2


class TestHashFileMetadata:
    """Tests for file metadata hashing."""

    def test_hash_file_metadata(self, temp_dir: Path) -> None:
        """Test hashing file metadata."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("Test")

        meta_hash = hash_file_metadata(file_path)
        assert len(meta_hash) == 16


class TestHashForCache:
    """Tests for cache key generation."""

    def test_hash_for_cache_format(self) -> None:
        """Test cache key format."""
        key = hash_for_cache("ls", content_hash="abc123")
        assert key.startswith("ls:")
        assert len(key) == 3 + 32  # "ls:" + 32 char hash

    def test_hash_for_cache_deterministic(self) -> None:
        """Test that same params produce same key."""
        key1 = hash_for_cache("cat", content_hash="abc", model="llama3")
        key2 = hash_for_cache("cat", content_hash="abc", model="llama3")
        assert key1 == key2

    def test_hash_for_cache_different_params(self) -> None:
        """Test that different params produce different keys."""
        key1 = hash_for_cache("cat", content_hash="abc")
        key2 = hash_for_cache("cat", content_hash="xyz")
        assert key1 != key2


class TestHashPrompt:
    """Tests for prompt hashing."""

    def test_hash_prompt(self) -> None:
        """Test prompt hashing."""
        prompt = "Describe this file"
        prompt_hash = hash_prompt(prompt)
        assert len(prompt_hash) == 16

    def test_hash_prompt_deterministic(self) -> None:
        """Test that same prompt produces same hash."""
        prompt = "Test prompt"
        assert hash_prompt(prompt) == hash_prompt(prompt)
