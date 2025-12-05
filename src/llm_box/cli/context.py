"""Context factory for creating CommandContext from CLI options.

This module provides utilities for creating a fully-configured
CommandContext from CLI arguments and configuration.
"""

from pathlib import Path
from typing import Any

from llm_box.cache import DuckDBCache
from llm_box.cache.base import Cache, CacheEntry
from llm_box.cli.options import FormatChoice, get_output_format, get_provider_type
from llm_box.commands.base import CommandContext
from llm_box.config import get_config
from llm_box.config.schema import LLMBoxConfig
from llm_box.output import get_formatter
from llm_box.output.base import OutputFormatter
from llm_box.providers.base import LLMBoxProvider, ProviderType
from llm_box.providers.registry import ProviderRegistry


class NullCache(Cache):
    """A no-op cache implementation for when caching is disabled."""

    def get(self, key: str) -> None:
        """Always returns None (cache miss)."""
        return None

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
        """No-op set, returns a dummy entry."""
        return CacheEntry(
            key=key,
            command=command,
            provider=provider,
            model=model,
            response=response,
            tokens_used=tokens_used,
            ttl_seconds=ttl_seconds,
            metadata=metadata or {},
        )

    def delete(self, key: str) -> bool:
        """No-op delete."""
        return False

    def clear(self) -> int:
        """No-op clear."""
        return 0

    def cleanup_expired(self) -> int:
        """No-op cleanup."""
        return 0

    def count(self) -> int:
        """Always returns 0."""
        return 0

    def stats(self) -> dict[str, Any]:
        """Return empty stats."""
        return {"enabled": False, "entries": 0, "hits": 0, "misses": 0}


def create_provider(
    provider_type: ProviderType,
    model: str | None = None,
    config: LLMBoxConfig | None = None,
) -> LLMBoxProvider:
    """Create an LLM provider from configuration.

    Args:
        provider_type: Type of provider to create.
        model: Optional model override.
        config: Configuration to use. If None, uses global config.

    Returns:
        Configured LLMBoxProvider instance.
    """
    if config is None:
        config = get_config()

    # Get provider-specific config and build kwargs
    default_model: str | None = None
    kwargs: dict[str, Any] = {}

    if provider_type == ProviderType.OLLAMA:
        ollama_config = config.providers.ollama
        default_model = ollama_config.default_model
        kwargs["base_url"] = ollama_config.base_url
    elif provider_type == ProviderType.OPENAI:
        openai_config = config.providers.openai
        default_model = openai_config.default_model
        if openai_config.api_key:
            kwargs["api_key"] = openai_config.api_key
    elif provider_type == ProviderType.ANTHROPIC:
        anthropic_config = config.providers.anthropic
        default_model = anthropic_config.default_model
        if anthropic_config.api_key:
            kwargs["api_key"] = anthropic_config.api_key

    return ProviderRegistry.get(
        provider_type,
        model=model or default_model,
        **kwargs,
    )


def create_cache(config: LLMBoxConfig | None = None, enabled: bool = True) -> Cache:
    """Create a cache instance from configuration.

    Args:
        config: Configuration to use. If None, uses global config.
        enabled: Whether caching is enabled. If False, returns NullCache.

    Returns:
        Cache instance (DuckDBCache or NullCache).
    """
    if config is None:
        config = get_config()

    if not enabled or not config.cache.enabled:
        return NullCache()

    return DuckDBCache(
        default_ttl=config.cache.default_ttl_seconds,
    )


def create_formatter(
    format_choice: FormatChoice | None = None,
    verbose: bool = False,
    config: LLMBoxConfig | None = None,
) -> OutputFormatter:
    """Create an output formatter from configuration.

    Args:
        format_choice: CLI format choice override.
        verbose: Whether to enable verbose output.
        config: Configuration to use. If None, uses global config.

    Returns:
        Configured OutputFormatter instance.
    """
    if config is None:
        config = get_config()

    output_format = get_output_format(format_choice, config.output.default_format)
    return get_formatter(output_format, verbose=verbose)


def create_context(
    *,
    provider: str | None = None,
    model: str | None = None,
    format_choice: FormatChoice | None = None,
    no_cache: bool = False,
    verbose: bool = False,
    working_dir: Path | None = None,
    config: LLMBoxConfig | None = None,
) -> CommandContext:
    """Create a CommandContext from CLI options.

    This is the main factory function for creating a fully-configured
    context for command execution.

    Args:
        provider: Provider name override (ollama, openai, anthropic).
        model: Model name override.
        format_choice: Output format override.
        no_cache: Whether to disable caching.
        verbose: Whether to enable verbose output.
        working_dir: Working directory for file operations.
        config: Configuration to use. If None, uses global config.

    Returns:
        Fully configured CommandContext.

    Example:
        ctx = create_context(
            provider="ollama",
            model="llama3",
            no_cache=True,
            verbose=True,
        )
        result = command.execute(ctx, file="example.py")
    """
    if config is None:
        config = get_config()

    # Determine provider type
    # config.default_provider may be ProviderType enum or string depending on source
    default_provider = (
        config.default_provider.value
        if hasattr(config.default_provider, "value")
        else str(config.default_provider)
    )
    provider_type = get_provider_type(provider, default_provider)

    # Create components
    llm_provider = create_provider(provider_type, model, config)
    cache = create_cache(config, enabled=not no_cache)
    formatter = create_formatter(format_choice, verbose, config)

    return CommandContext(
        provider=llm_provider,
        cache=cache,
        formatter=formatter,
        config=config,
        use_cache=not no_cache,
        verbose=verbose,
        working_dir=working_dir or Path.cwd(),
    )
