"""OpenAI provider implementation using LangChain."""

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


class OpenAIProvider(LLMBoxProvider):
    """OpenAI provider using LangChain integration.

    Requires langchain-openai package:
        pip install llm-box[openai]
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        embedding_model: str = "text-embedding-3-small",
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        """Initialize OpenAI provider.

        Args:
            model: Chat model name (e.g., "gpt-4o-mini", "gpt-4o").
            api_key: OpenAI API key (uses OPENAI_API_KEY env var if None).
            embedding_model: Embedding model name.
            timeout: Request timeout in seconds.
            **kwargs: Additional arguments passed to ChatOpenAI.
        """
        super().__init__(ProviderType.OPENAI, model)
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._embedding_model = embedding_model
        self._timeout = timeout
        self._extra_kwargs = kwargs

        if not self._api_key:
            raise ProviderAuthError(
                "OpenAI API key not provided. "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        # Lazy initialization
        self._chat_model = None
        self._embeddings_model = None

    def _get_chat_model(self) -> Any:
        """Lazily initialize and return the chat model."""
        if self._chat_model is None:
            try:
                from langchain_openai import ChatOpenAI
            except ImportError as e:
                raise ProviderError(
                    "langchain-openai not installed. "
                    "Install with: pip install llm-box[openai]"
                ) from e

            self._chat_model = ChatOpenAI(
                model=self.model_name,
                api_key=self._api_key,
                timeout=self._timeout,
                **self._extra_kwargs,
            )
        return self._chat_model

    def _get_embeddings_model(self) -> Any:
        """Lazily initialize and return the embeddings model."""
        if self._embeddings_model is None:
            try:
                from langchain_openai import OpenAIEmbeddings
            except ImportError as e:
                raise ProviderError(
                    "langchain-openai not installed. "
                    "Install with: pip install llm-box[openai]"
                ) from e

            self._embeddings_model = OpenAIEmbeddings(
                model=self._embedding_model,
                api_key=self._api_key,
            )
        return self._embeddings_model

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_embeddings(self) -> bool:
        return True

    def _handle_error(self, e: Exception) -> None:
        """Convert exceptions to appropriate provider errors."""
        error_str = str(e).lower()

        if "authentication" in error_str or "invalid api key" in error_str:
            raise ProviderAuthError(
                "OpenAI authentication failed. Check your API key."
            ) from e

        if "rate limit" in error_str or "429" in error_str:
            raise ProviderRateLimitError(
                "OpenAI rate limit exceeded. Try again later."
            ) from e

        if "timeout" in error_str:
            raise ProviderTimeoutError(
                f"OpenAI request timed out after {self._timeout}s"
            ) from e

        raise ProviderError(f"OpenAI error: {e}") from e

    def invoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Synchronously invoke OpenAI."""
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
                    "finish_reason"
                ),
            )
        except Exception as e:
            self._handle_error(e)
            raise

    async def ainvoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Asynchronously invoke OpenAI."""
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
                    "finish_reason"
                ),
            )
        except Exception as e:
            self._handle_error(e)
            raise

    async def astream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        """Stream response tokens from OpenAI."""
        try:
            chat = self._get_chat_model()
            async for chunk in chat.astream(prompt, **kwargs):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            self._handle_error(e)
            raise

    def _embed_impl(self, texts: list[str], **kwargs: Any) -> EmbeddingResponse:
        """Generate embeddings using OpenAI."""
        try:
            embeddings_model = self._get_embeddings_model()
            vectors = embeddings_model.embed_documents(texts)

            return EmbeddingResponse(
                embeddings=vectors,
                model=self._embedding_model,
                provider=self.provider_type,
                dimensions=len(vectors[0]) if vectors else 0,
                tokens_used=None,
            )
        except Exception as e:
            self._handle_error(e)
            raise


@ProviderRegistry.register(ProviderType.OPENAI)
def create_openai_provider(
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
    embedding_model: str = "text-embedding-3-small",
    timeout: float = 60.0,
    **kwargs: Any,
) -> OpenAIProvider:
    """Factory function to create an OpenAI provider.

    Args:
        model: Chat model name.
        api_key: OpenAI API key (uses OPENAI_API_KEY env var if None).
        embedding_model: Embedding model name.
        timeout: Request timeout in seconds.
        **kwargs: Additional arguments.

    Returns:
        OpenAIProvider instance.
    """
    return OpenAIProvider(
        model=model,
        api_key=api_key,
        embedding_model=embedding_model,
        timeout=timeout,
        **kwargs,
    )
