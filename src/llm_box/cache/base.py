"""Cache protocol and base classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CacheEntry:
    """Represents a cached LLM response.

    Attributes:
        key: Unique cache key.
        command: The command that generated this entry (e.g., "ls", "cat").
        provider: The LLM provider used (e.g., "ollama", "openai").
        model: The model name.
        response: The cached response content.
        tokens_used: Number of tokens used (if available).
        created_at: When the entry was created.
        ttl_seconds: Time-to-live in seconds (None means no expiration).
        metadata: Additional metadata about the cached entry.
    """

    key: str
    command: str
    provider: str
    model: str
    response: str
    tokens_used: int | None = None
    created_at: datetime = field(default_factory=datetime.now)
    ttl_seconds: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl_seconds


class Cache(ABC):
    """Abstract base class for cache implementations.

    This defines the interface that all cache backends must implement.
    """

    @abstractmethod
    def get(self, key: str) -> CacheEntry | None:
        """Retrieve an entry from the cache.

        Args:
            key: The cache key to look up.

        Returns:
            CacheEntry if found and not expired, None otherwise.
        """
        pass

    @abstractmethod
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
            ttl_seconds: Time-to-live in seconds (optional).
            metadata: Additional metadata (optional).

        Returns:
            The created CacheEntry.
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete an entry from the cache.

        Args:
            key: The cache key to delete.

        Returns:
            True if the entry was deleted, False if it didn't exist.
        """
        pass

    @abstractmethod
    def clear(self) -> int:
        """Clear all entries from the cache.

        Returns:
            The number of entries that were cleared.
        """
        pass

    @abstractmethod
    def cleanup_expired(self) -> int:
        """Remove all expired entries from the cache.

        Returns:
            The number of entries that were removed.
        """
        pass

    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache and is not expired.

        Args:
            key: The cache key to check.

        Returns:
            True if the key exists and is not expired.
        """
        return self.get(key) is not None

    @abstractmethod
    def count(self) -> int:
        """Get the total number of entries in the cache.

        Returns:
            The number of cached entries.
        """
        pass

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics like hit rate, size, etc.
        """
        pass
