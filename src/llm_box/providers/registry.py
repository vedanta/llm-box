"""Provider registry for creating and caching provider instances."""

from collections.abc import Callable
from typing import Any, TypeVar

from llm_box.exceptions import ProviderError, ProviderNotAvailableError
from llm_box.providers.base import LLMBoxProvider, ProviderType

# Type for provider factory functions
ProviderFactory = Callable[..., LLMBoxProvider]
T = TypeVar("T", bound=LLMBoxProvider)


class ProviderRegistry:
    """Factory for creating and caching provider instances.

    This registry manages provider factories and caches instances
    to avoid creating multiple instances for the same configuration.

    Usage:
        # Register a provider factory
        @ProviderRegistry.register(ProviderType.OLLAMA)
        def create_ollama(model: str = "llama3", **kwargs) -> OllamaProvider:
            return OllamaProvider(model=model, **kwargs)

        # Get a provider instance
        provider = ProviderRegistry.get(ProviderType.OLLAMA, model="llama3")
    """

    _factories: dict[ProviderType, ProviderFactory] = {}
    _instances: dict[str, LLMBoxProvider] = {}

    @classmethod
    def register(
        cls, provider_type: ProviderType
    ) -> Callable[[ProviderFactory], ProviderFactory]:
        """Decorator to register a provider factory.

        Args:
            provider_type: The type of provider this factory creates.

        Returns:
            Decorator function.

        Example:
            @ProviderRegistry.register(ProviderType.OLLAMA)
            def create_ollama(**kwargs) -> OllamaProvider:
                return OllamaProvider(**kwargs)
        """

        def decorator(factory: ProviderFactory) -> ProviderFactory:
            cls._factories[provider_type] = factory
            return factory

        return decorator

    @classmethod
    def get(
        cls,
        provider_type: ProviderType,
        model: str | None = None,
        *,
        use_cache: bool = True,
        **kwargs: Any,
    ) -> LLMBoxProvider:
        """Get or create a provider instance.

        Args:
            provider_type: Type of provider to get.
            model: Model name (uses provider default if None).
            use_cache: Whether to cache/reuse instances.
            **kwargs: Additional arguments for the provider factory.

        Returns:
            Provider instance.

        Raises:
            ProviderNotAvailableError: If provider type is not registered.
            ProviderError: If provider creation fails.
        """
        # Check if provider is registered
        factory = cls._factories.get(provider_type)
        if factory is None:
            available = [p.value for p in cls._factories]
            raise ProviderNotAvailableError(
                f"Provider '{provider_type.value}' is not registered. "
                f"Available providers: {available}"
            )

        # Build cache key
        cache_key = cls._build_cache_key(provider_type, model, **kwargs)

        # Check cache
        if use_cache and cache_key in cls._instances:
            return cls._instances[cache_key]

        # Create new instance
        try:
            if model is not None:
                instance = factory(model=model, **kwargs)
            else:
                instance = factory(**kwargs)
        except Exception as e:
            raise ProviderError(
                f"Failed to create provider '{provider_type.value}': {e}"
            ) from e

        # Cache instance
        if use_cache:
            cls._instances[cache_key] = instance

        return instance

    @classmethod
    def _build_cache_key(
        cls,
        provider_type: ProviderType,
        model: str | None,
        **kwargs: Any,
    ) -> str:
        """Build a cache key for provider instances."""
        # Sort kwargs for deterministic key
        sorted_kwargs = sorted(kwargs.items())
        kwargs_str = ",".join(f"{k}={v}" for k, v in sorted_kwargs)
        return f"{provider_type.value}:{model or 'default'}:{kwargs_str}"

    @classmethod
    def list_available(cls) -> list[ProviderType]:
        """List all registered provider types.

        Returns:
            List of available provider types.
        """
        return list(cls._factories.keys())

    @classmethod
    def is_registered(cls, provider_type: ProviderType) -> bool:
        """Check if a provider type is registered.

        Args:
            provider_type: Provider type to check.

        Returns:
            True if registered, False otherwise.
        """
        return provider_type in cls._factories

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached provider instances."""
        cls._instances.clear()

    @classmethod
    def clear_factories(cls) -> None:
        """Clear all registered factories (mainly for testing)."""
        cls._factories.clear()
        cls._instances.clear()

    @classmethod
    def get_cached_count(cls) -> int:
        """Get the number of cached provider instances."""
        return len(cls._instances)
