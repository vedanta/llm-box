"""LLM provider abstraction layer.

This module provides a unified interface for interacting with
different LLM backends (Ollama, OpenAI, Anthropic).

Usage:
    from llm_box.providers import ProviderRegistry, ProviderType

    # Get a provider
    provider = ProviderRegistry.get(ProviderType.OLLAMA, model="llama3")

    # Invoke the LLM
    response = provider.invoke("Explain this code")
    print(response.content)

    # Generate embeddings
    embeddings = provider.embed(["text1", "text2"])
"""

import contextlib

# Import providers to register them
from llm_box.providers.base import (
    EmbeddingResponse,
    LLMBoxProvider,
    LLMResponse,
    ProviderType,
)
from llm_box.providers.fallback import (
    FallbackProvider,
    ainvoke_with_fallback,
    embed_with_fallback,
    invoke_with_fallback,
)
from llm_box.providers.mock import MockProvider
from llm_box.providers.registry import ProviderRegistry

# Optional providers - import only if dependencies are available
with contextlib.suppress(ImportError):
    from llm_box.providers import ollama  # noqa: F401

with contextlib.suppress(ImportError):
    from llm_box.providers import openai  # noqa: F401

with contextlib.suppress(ImportError):
    from llm_box.providers import anthropic  # noqa: F401

__all__ = [
    # Base classes
    "LLMBoxProvider",
    "LLMResponse",
    "EmbeddingResponse",
    "ProviderType",
    # Registry
    "ProviderRegistry",
    # Providers
    "MockProvider",
    # Fallback
    "FallbackProvider",
    "invoke_with_fallback",
    "ainvoke_with_fallback",
    "embed_with_fallback",
]
