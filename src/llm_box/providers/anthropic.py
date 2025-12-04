"""Anthropic provider implementation using LangChain."""

import os
from collections.abc import AsyncIterator
from typing import Any

from llm_box.exceptions import (
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from llm_box.providers.base import (
    EmbeddingResponse,
    LLMBoxProvider,
    LLMResponse,
    ProviderType,
)
from llm_box.providers.registry import ProviderRegistry


class AnthropicProvider(LLMBoxProvider):
    """Anthropic (Claude) provider using LangChain integration.

    Requires langchain-anthropic package:
        pip install llm-box[anthropic]

    Note: Anthropic doesn't have an embeddings API, so embeddings
    are not supported unless a fallback is configured.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        max_tokens: int = 4096,
        timeout: float = 60.0,
        embeddings_fallback: LLMBoxProvider | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Anthropic provider.

        Args:
            model: Model name (e.g., "claude-sonnet-4-20250514", "claude-3-opus-20240229").
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if None).
            max_tokens: Maximum tokens in response.
            timeout: Request timeout in seconds.
            embeddings_fallback: Optional provider to use for embeddings.
            **kwargs: Additional arguments passed to ChatAnthropic.
        """
        super().__init__(ProviderType.ANTHROPIC, model)
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._embeddings_fallback = embeddings_fallback
        self._extra_kwargs = kwargs

        if not self._api_key:
            raise ProviderAuthError(
                "Anthropic API key not provided. "
                "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        # Lazy initialization
        self._chat_model = None

    def _get_chat_model(self) -> Any:
        """Lazily initialize and return the chat model."""
        if self._chat_model is None:
            try:
                from langchain_anthropic import ChatAnthropic
            except ImportError as e:
                raise ProviderError(
                    "langchain-anthropic not installed. "
                    "Install with: pip install llm-box[anthropic]"
                ) from e

            self._chat_model = ChatAnthropic(
                model=self.model_name,
                api_key=self._api_key,
                max_tokens=self._max_tokens,
                timeout=self._timeout,
                **self._extra_kwargs,
            )
        return self._chat_model

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_embeddings(self) -> bool:
        # Only supports embeddings if a fallback provider is configured
        return self._embeddings_fallback is not None

    def _handle_error(self, e: Exception) -> None:
        """Convert exceptions to appropriate provider errors."""
        error_str = str(e).lower()

        if (
            "authentication" in error_str
            or "invalid" in error_str
            and "key" in error_str
        ):
            raise ProviderAuthError(
                "Anthropic authentication failed. Check your API key."
            ) from e

        if "rate limit" in error_str or "429" in error_str:
            raise ProviderRateLimitError(
                "Anthropic rate limit exceeded. Try again later."
            ) from e

        if "timeout" in error_str:
            raise ProviderTimeoutError(
                f"Anthropic request timed out after {self._timeout}s"
            ) from e

        raise ProviderError(f"Anthropic error: {e}") from e

    def invoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Synchronously invoke Anthropic."""
        try:
            chat = self._get_chat_model()
            response = chat.invoke(prompt, **kwargs)

            tokens_used = None
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens_used = response.usage_metadata.get("total_tokens")

            return LLMResponse(
                content=response.content,
                model=self.model_name,
                provider=self.provider_type,
                tokens_used=tokens_used,
                finish_reason=getattr(response, "response_metadata", {}).get(
                    "stop_reason"
                ),
            )
        except Exception as e:
            self._handle_error(e)
            raise

    async def ainvoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Asynchronously invoke Anthropic."""
        try:
            chat = self._get_chat_model()
            response = await chat.ainvoke(prompt, **kwargs)

            tokens_used = None
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens_used = response.usage_metadata.get("total_tokens")

            return LLMResponse(
                content=response.content,
                model=self.model_name,
                provider=self.provider_type,
                tokens_used=tokens_used,
                finish_reason=getattr(response, "response_metadata", {}).get(
                    "stop_reason"
                ),
            )
        except Exception as e:
            self._handle_error(e)
            raise

    async def astream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        """Stream response tokens from Anthropic."""
        try:
            chat = self._get_chat_model()
            async for chunk in chat.astream(prompt, **kwargs):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            self._handle_error(e)
            raise

    def _embed_impl(self, texts: list[str], **kwargs: Any) -> EmbeddingResponse:
        """Generate embeddings using fallback provider.

        Anthropic doesn't have an embeddings API, so we delegate
        to a fallback provider if one is configured.
        """
        if self._embeddings_fallback is None:
            raise NotImplementedError(
                "Anthropic does not support embeddings. "
                "Configure an embeddings_fallback provider (e.g., OpenAI)."
            )

        return self._embeddings_fallback.embed(texts, **kwargs)


@ProviderRegistry.register(ProviderType.ANTHROPIC)
def create_anthropic_provider(
    model: str = "claude-sonnet-4-20250514",
    api_key: str | None = None,
    max_tokens: int = 4096,
    timeout: float = 60.0,
    **kwargs: Any,
) -> AnthropicProvider:
    """Factory function to create an Anthropic provider.

    Args:
        model: Model name.
        api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if None).
        max_tokens: Maximum tokens in response.
        timeout: Request timeout in seconds.
        **kwargs: Additional arguments.

    Returns:
        AnthropicProvider instance.
    """
    return AnthropicProvider(
        model=model,
        api_key=api_key,
        max_tokens=max_tokens,
        timeout=timeout,
        **kwargs,
    )
