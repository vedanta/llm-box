"""Ollama provider implementation using LangChain."""

from collections.abc import AsyncIterator
from typing import Any

from llm_box.exceptions import (
    ProviderError,
    ProviderNotAvailableError,
    ProviderTimeoutError,
)
from llm_box.providers.base import (
    EmbeddingResponse,
    LLMBoxProvider,
    LLMResponse,
    ProviderType,
)
from llm_box.providers.registry import ProviderRegistry


class OllamaProvider(LLMBoxProvider):
    """Ollama provider using LangChain integration.

    Requires langchain-ollama package:
        pip install llm-box[ollama]
    """

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
        **kwargs: Any,
    ) -> None:
        """Initialize Ollama provider.

        Args:
            model: Model name (e.g., "llama3", "mistral", "codellama").
            base_url: Ollama server URL.
            timeout: Request timeout in seconds.
            **kwargs: Additional arguments passed to ChatOllama.
        """
        super().__init__(ProviderType.OLLAMA, model)
        self._base_url = base_url
        self._timeout = timeout
        self._extra_kwargs = kwargs

        # Lazy initialization of LangChain models
        self._chat_model: Any = None
        self._embeddings_model: Any = None

    def _get_chat_model(self) -> Any:
        """Lazily initialize and return the chat model."""
        if self._chat_model is None:
            try:
                from langchain_ollama import ChatOllama
            except ImportError as e:
                raise ProviderError(
                    "langchain-ollama not installed. "
                    "Install with: pip install llm-box[ollama]"
                ) from e

            self._chat_model = ChatOllama(
                model=self.model_name,
                base_url=self._base_url,
                **self._extra_kwargs,
            )
        return self._chat_model

    def _get_embeddings_model(self) -> Any:
        """Lazily initialize and return the embeddings model."""
        if self._embeddings_model is None:
            try:
                from langchain_ollama import OllamaEmbeddings
            except ImportError as e:
                raise ProviderError(
                    "langchain-ollama not installed. "
                    "Install with: pip install llm-box[ollama]"
                ) from e

            self._embeddings_model = OllamaEmbeddings(
                model=self.model_name,
                base_url=self._base_url,
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

        if "connection" in error_str or "refused" in error_str:
            raise ProviderNotAvailableError(
                f"Cannot connect to Ollama at {self._base_url}. "
                "Make sure Ollama is running: ollama serve"
            ) from e

        if "timeout" in error_str:
            raise ProviderTimeoutError(
                f"Request to Ollama timed out after {self._timeout}s"
            ) from e

        raise ProviderError(f"Ollama error: {e}") from e

    def invoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Synchronously invoke Ollama."""
        try:
            chat = self._get_chat_model()
            response = chat.invoke(prompt, **kwargs)

            # Extract token usage if available
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
            raise  # Should not reach here

    async def ainvoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Asynchronously invoke Ollama."""
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
        """Stream response tokens from Ollama."""
        try:
            chat = self._get_chat_model()
            async for chunk in chat.astream(prompt, **kwargs):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            self._handle_error(e)
            raise

    def _embed_impl(self, texts: list[str], **kwargs: Any) -> EmbeddingResponse:
        """Generate embeddings using Ollama."""
        try:
            embeddings_model = self._get_embeddings_model()
            vectors = embeddings_model.embed_documents(texts)

            return EmbeddingResponse(
                embeddings=vectors,
                model=self.model_name,
                provider=self.provider_type,
                dimensions=len(vectors[0]) if vectors else 0,
                tokens_used=None,  # Ollama doesn't report token usage for embeddings
            )
        except Exception as e:
            self._handle_error(e)
            raise


@ProviderRegistry.register(ProviderType.OLLAMA)
def create_ollama_provider(
    model: str = "llama3",
    base_url: str = "http://localhost:11434",
    timeout: float = 120.0,
    **kwargs: Any,
) -> OllamaProvider:
    """Factory function to create an Ollama provider.

    Args:
        model: Model name (e.g., "llama3", "mistral").
        base_url: Ollama server URL.
        timeout: Request timeout in seconds.
        **kwargs: Additional arguments.

    Returns:
        OllamaProvider instance.
    """
    return OllamaProvider(
        model=model,
        base_url=base_url,
        timeout=timeout,
        **kwargs,
    )
