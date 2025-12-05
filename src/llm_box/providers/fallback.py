"""Multi-provider fallback logic."""

from typing import Any

from llm_box.exceptions import ProviderError
from llm_box.providers.base import EmbeddingResponse, LLMBoxProvider, LLMResponse


def invoke_with_fallback(
    providers: list[LLMBoxProvider],
    prompt: str,
    **kwargs: Any,
) -> LLMResponse:
    """Try providers in order until one succeeds.

    Args:
        providers: List of providers to try, in order of preference.
        prompt: The prompt to send to the LLM.
        **kwargs: Additional arguments passed to invoke.

    Returns:
        LLMResponse from the first successful provider.

    Raises:
        ProviderError: If all providers fail.
        ValueError: If providers list is empty.
    """
    if not providers:
        raise ValueError("At least one provider must be specified")

    errors: list[tuple[str, str]] = []

    for provider in providers:
        try:
            return provider.invoke(prompt, **kwargs)
        except ProviderError as e:
            errors.append((provider.provider_type.value, str(e)))
            continue
        except Exception as e:
            errors.append((provider.provider_type.value, str(e)))
            continue

    # All providers failed
    error_details = "; ".join(f"{p}: {e}" for p, e in errors)
    raise ProviderError(f"All providers failed: {error_details}")


async def ainvoke_with_fallback(
    providers: list[LLMBoxProvider],
    prompt: str,
    **kwargs: Any,
) -> LLMResponse:
    """Try providers in order until one succeeds (async version).

    Args:
        providers: List of providers to try, in order of preference.
        prompt: The prompt to send to the LLM.
        **kwargs: Additional arguments passed to ainvoke.

    Returns:
        LLMResponse from the first successful provider.

    Raises:
        ProviderError: If all providers fail.
        ValueError: If providers list is empty.
    """
    if not providers:
        raise ValueError("At least one provider must be specified")

    errors: list[tuple[str, str]] = []

    for provider in providers:
        try:
            return await provider.ainvoke(prompt, **kwargs)
        except ProviderError as e:
            errors.append((provider.provider_type.value, str(e)))
            continue
        except Exception as e:
            errors.append((provider.provider_type.value, str(e)))
            continue

    # All providers failed
    error_details = "; ".join(f"{p}: {e}" for p, e in errors)
    raise ProviderError(f"All providers failed: {error_details}")


def embed_with_fallback(
    providers: list[LLMBoxProvider],
    texts: list[str],
    **kwargs: Any,
) -> EmbeddingResponse:
    """Try providers in order until one succeeds for embeddings.

    Args:
        providers: List of providers to try, in order of preference.
        texts: List of texts to embed.
        **kwargs: Additional arguments passed to embed.

    Returns:
        EmbeddingResponse from the first successful provider.

    Raises:
        ProviderError: If all providers fail.
        ValueError: If providers list is empty.
    """
    if not providers:
        raise ValueError("At least one provider must be specified")

    errors: list[tuple[str, str]] = []

    for provider in providers:
        if not provider.supports_embeddings:
            errors.append((provider.provider_type.value, "Does not support embeddings"))
            continue

        try:
            return provider.embed(texts, **kwargs)
        except ProviderError as e:
            errors.append((provider.provider_type.value, str(e)))
            continue
        except Exception as e:
            errors.append((provider.provider_type.value, str(e)))
            continue

    # All providers failed
    error_details = "; ".join(f"{p}: {e}" for p, e in errors)
    raise ProviderError(f"All providers failed for embeddings: {error_details}")


class FallbackProvider(LLMBoxProvider):
    """A provider that wraps multiple providers with fallback logic.

    This allows using a chain of providers as a single provider instance.
    """

    def __init__(
        self,
        providers: list[LLMBoxProvider],
        name: str = "fallback",
    ) -> None:
        """Initialize fallback provider.

        Args:
            providers: List of providers in order of preference.
            name: Name for this fallback provider.

        Raises:
            ValueError: If providers list is empty.
        """
        if not providers:
            raise ValueError("At least one provider must be specified")

        # Use the first provider's type for compatibility
        from llm_box.providers.base import ProviderType

        super().__init__(ProviderType.MOCK, name)  # Use MOCK as placeholder type
        self._providers = providers
        self._name = name

    @property
    def supports_streaming(self) -> bool:
        # Streaming is complex with fallback, disable for now
        return False

    @property
    def supports_embeddings(self) -> bool:
        return any(p.supports_embeddings for p in self._providers)

    @property
    def primary_provider(self) -> LLMBoxProvider:
        """Get the primary (first) provider."""
        return self._providers[0]

    def invoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Invoke with fallback logic."""
        return invoke_with_fallback(self._providers, prompt, **kwargs)

    async def ainvoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Async invoke with fallback logic."""
        return await ainvoke_with_fallback(self._providers, prompt, **kwargs)

    def _embed_impl(self, texts: list[str], **kwargs: Any) -> EmbeddingResponse:
        """Embed with fallback logic."""
        return embed_with_fallback(self._providers, texts, **kwargs)

    def __repr__(self) -> str:
        provider_names = [p.provider_type.value for p in self._providers]
        return f"FallbackProvider(providers={provider_names})"
