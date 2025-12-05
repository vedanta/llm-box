"""Base provider class and types for LLM abstraction."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: str
    model: str
    provider: ProviderType
    tokens_used: int | None = None
    finish_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbeddingResponse:
    """Response containing vector embeddings."""

    embeddings: list[list[float]]
    model: str
    provider: ProviderType
    dimensions: int
    tokens_used: int | None = None


class LLMBoxProvider(ABC):
    """Abstract base class for LLM providers.

    All providers must implement this interface to ensure consistent
    behavior across different LLM backends (Ollama, OpenAI, Anthropic).
    """

    def __init__(
        self,
        provider_type: ProviderType,
        model_name: str,
    ) -> None:
        """Initialize the provider.

        Args:
            provider_type: Type of provider (ollama, openai, etc.)
            model_name: Name of the model to use.
        """
        self._provider_type = provider_type
        self._model_name = model_name

    @property
    def provider_type(self) -> ProviderType:
        """Get the provider type."""
        return self._provider_type

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._model_name

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming responses."""
        ...

    @property
    @abstractmethod
    def supports_embeddings(self) -> bool:
        """Whether this provider supports generating embeddings."""
        ...

    @abstractmethod
    def invoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Synchronously invoke the LLM.

        Args:
            prompt: The prompt to send to the LLM.
            **kwargs: Additional provider-specific arguments.

        Returns:
            LLMResponse with the generated content.

        Raises:
            ProviderError: If the invocation fails.
        """
        ...

    @abstractmethod
    async def ainvoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Asynchronously invoke the LLM.

        Args:
            prompt: The prompt to send to the LLM.
            **kwargs: Additional provider-specific arguments.

        Returns:
            LLMResponse with the generated content.

        Raises:
            ProviderError: If the invocation fails.
        """
        ...

    async def astream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        """Stream response tokens asynchronously.

        Args:
            prompt: The prompt to send to the LLM.
            **kwargs: Additional provider-specific arguments.

        Yields:
            String tokens as they are generated.

        Raises:
            ProviderError: If streaming fails.
            NotImplementedError: If provider doesn't support streaming.
        """
        if not self.supports_streaming:
            raise NotImplementedError(
                f"Provider {self.provider_type} does not support streaming"
            )
        # Default implementation - subclasses should override for true streaming
        response = await self.ainvoke(prompt, **kwargs)
        yield response.content

    def embed(self, texts: list[str], **kwargs: Any) -> EmbeddingResponse:
        """Generate embeddings for texts.

        Args:
            texts: List of texts to embed.
            **kwargs: Additional provider-specific arguments.

        Returns:
            EmbeddingResponse with the embeddings.

        Raises:
            ProviderError: If embedding fails.
            NotImplementedError: If provider doesn't support embeddings.
        """
        if not self.supports_embeddings:
            raise NotImplementedError(
                f"Provider {self.provider_type} does not support embeddings"
            )
        return self._embed_impl(texts, **kwargs)

    def _embed_impl(self, texts: list[str], **kwargs: Any) -> EmbeddingResponse:
        """Implementation of embedding generation.

        Subclasses should override this method.
        """
        raise NotImplementedError("Subclass must implement _embed_impl")

    def health_check(self) -> bool:
        """Check if the provider is available and responding.

        Returns:
            True if provider is healthy, False otherwise.
        """
        try:
            self.invoke("Hello")
            return True
        except Exception:
            return False

    async def ahealth_check(self) -> bool:
        """Async health check.

        Returns:
            True if provider is healthy, False otherwise.
        """
        try:
            await self.ainvoke("Hello")
            return True
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider_type.value}, model={self.model_name})"
