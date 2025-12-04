"""Mock provider for testing."""

import asyncio
import hashlib
from collections.abc import AsyncIterator
from typing import Any

from llm_box.providers.base import (
    EmbeddingResponse,
    LLMBoxProvider,
    LLMResponse,
    ProviderType,
)
from llm_box.providers.registry import ProviderRegistry


class MockProvider(LLMBoxProvider):
    """Mock LLM provider for testing.

    Generates deterministic responses based on input, making tests predictable.
    Can be configured with custom responses for specific prompts.
    """

    def __init__(
        self,
        model: str = "mock-model",
        responses: dict[str, str] | None = None,
        embedding_dimensions: int = 128,
        latency_ms: int = 0,
    ) -> None:
        """Initialize mock provider.

        Args:
            model: Model name to report.
            responses: Dict mapping prompt substrings to responses.
            embedding_dimensions: Dimension of fake embeddings.
            latency_ms: Simulated latency in milliseconds.
        """
        super().__init__(ProviderType.MOCK, model)
        self._responses = responses or {}
        self._embedding_dimensions = embedding_dimensions
        self._latency_ms = latency_ms
        self._call_history: list[dict[str, Any]] = []

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_embeddings(self) -> bool:
        return True

    @property
    def call_history(self) -> list[dict[str, Any]]:
        """Get history of all calls made to this provider."""
        return self._call_history

    @property
    def call_count(self) -> int:
        """Get the number of calls made to this provider."""
        return len(self._call_history)

    def clear_history(self) -> None:
        """Clear call history."""
        self._call_history.clear()

    def _generate_response(self, prompt: str) -> str:
        """Generate a deterministic response based on the prompt."""
        # Check for configured responses
        for key, response in self._responses.items():
            if key.lower() in prompt.lower():
                return response

        # Default: generate deterministic response from prompt hash
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:8]
        return f"Mock response for prompt (hash: {prompt_hash}): {prompt[:50]}..."

    def _record_call(self, method: str, prompt: str, **kwargs: Any) -> None:
        """Record a call to the provider."""
        self._call_history.append(
            {
                "method": method,
                "prompt": prompt,
                "kwargs": kwargs,
            }
        )

    def invoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Synchronously invoke the mock LLM."""
        self._record_call("invoke", prompt, **kwargs)

        # Simulate latency
        if self._latency_ms > 0:
            import time

            time.sleep(self._latency_ms / 1000)

        content = self._generate_response(prompt)

        return LLMResponse(
            content=content,
            model=self.model_name,
            provider=self.provider_type,
            tokens_used=len(prompt.split()) + len(content.split()),
            finish_reason="stop",
        )

    async def ainvoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Asynchronously invoke the mock LLM."""
        self._record_call("ainvoke", prompt, **kwargs)

        # Simulate latency
        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000)

        content = self._generate_response(prompt)

        return LLMResponse(
            content=content,
            model=self.model_name,
            provider=self.provider_type,
            tokens_used=len(prompt.split()) + len(content.split()),
            finish_reason="stop",
        )

    async def astream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        """Stream mock response tokens."""
        self._record_call("astream", prompt, **kwargs)

        # Simulate latency
        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000)

        content = self._generate_response(prompt)

        # Stream word by word
        words = content.split()
        for i, word in enumerate(words):
            if i < len(words) - 1:
                yield word + " "
            else:
                yield word

    def _embed_impl(self, texts: list[str], **kwargs: Any) -> EmbeddingResponse:
        """Generate deterministic fake embeddings."""
        self._record_call("embed", str(texts), **kwargs)

        embeddings = []
        for text in texts:
            # Generate deterministic embedding from text hash
            hash_bytes = hashlib.sha256(text.encode()).digest()
            # Extend hash to reach desired dimensions
            extended = hash_bytes * (self._embedding_dimensions // 32 + 1)
            # Convert to floats normalized to [-1, 1]
            embedding = [
                (b - 128) / 128.0 for b in extended[: self._embedding_dimensions]
            ]
            embeddings.append(embedding)

        return EmbeddingResponse(
            embeddings=embeddings,
            model=self.model_name,
            provider=self.provider_type,
            dimensions=self._embedding_dimensions,
            tokens_used=sum(len(t.split()) for t in texts),
        )


@ProviderRegistry.register(ProviderType.MOCK)
def create_mock_provider(
    model: str = "mock-model",
    responses: dict[str, str] | None = None,
    embedding_dimensions: int = 128,
    latency_ms: int = 0,
    **kwargs: Any,
) -> MockProvider:
    """Factory function to create a mock provider.

    Args:
        model: Model name to report.
        responses: Dict mapping prompt substrings to responses.
        embedding_dimensions: Dimension of fake embeddings.
        latency_ms: Simulated latency in milliseconds.
        **kwargs: Additional arguments (ignored).

    Returns:
        MockProvider instance.
    """
    return MockProvider(
        model=model,
        responses=responses,
        embedding_dimensions=embedding_dimensions,
        latency_ms=latency_ms,
    )
