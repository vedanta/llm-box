"""Caching layer using DuckDB.

This module provides a caching system for LLM responses using DuckDB
as the storage backend.

Usage:
    from llm_box.cache import DuckDBCache, generate_cache_key

    # Create a cache instance
    cache = DuckDBCache()

    # Generate a cache key
    key = generate_cache_key("cat", "ollama", "llama3", prompt="Explain this code")

    # Check for cached response
    entry = cache.get(key)
    if entry:
        print(f"Cache hit: {entry.response}")
    else:
        # Call LLM and cache the response
        response = "..."
        cache.set(key, "cat", "ollama", "llama3", response)
"""

from llm_box.cache.base import Cache, CacheEntry
from llm_box.cache.duckdb_cache import DuckDBCache, get_default_cache_path
from llm_box.cache.keys import (
    generate_cache_key,
    generate_file_key,
    generate_prompt_key,
    parse_cache_key,
)

__all__ = [
    # Base classes
    "Cache",
    "CacheEntry",
    # DuckDB implementation
    "DuckDBCache",
    "get_default_cache_path",
    # Key generation
    "generate_cache_key",
    "generate_prompt_key",
    "generate_file_key",
    "parse_cache_key",
]
