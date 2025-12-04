# LLM Provider Design

## Overview

The provider layer abstracts LLM interactions, enabling llm-box to work with multiple backends (Ollama, OpenAI, Anthropic) through a unified interface. We use LangChain as the underlying framework for consistent behavior.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Provider Registry                         │
│                    (providers/registry.py)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────┐ │
│  │   Ollama    │  │   OpenAI    │  │  Anthropic  │  │  Mock  │ │
│  │  Provider   │  │  Provider   │  │  Provider   │  │Provider│ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └───┬────┘ │
│         │                │                │              │      │
│         └────────────────┴────────────────┴──────────────┘      │
│                                  │                               │
│                                  ▼                               │
│                        ┌─────────────────┐                      │
│                        │  LLMBoxProvider │                      │
│                        │   (base class)  │                      │
│                        └─────────────────┘                      │
│                                  │                               │
│                    ┌─────────────┴─────────────┐                │
│                    ▼                           ▼                │
│           ┌─────────────────┐        ┌─────────────────┐       │
│           │   ChatModel     │        │   Embeddings    │       │
│           │  (LangChain)    │        │  (LangChain)    │       │
│           └─────────────────┘        └─────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## Base Provider Class

```python
# providers/base.py

from dataclasses import dataclass
from typing import Optional, AsyncIterator
from enum import Enum
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings


class ProviderType(str, Enum):
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
    tokens_used: Optional[int] = None


@dataclass
class EmbeddingResponse:
    """Response containing vector embeddings."""
    embeddings: list[list[float]]
    model: str
    dimensions: int


class LLMBoxProvider:
    """Unified wrapper around LangChain models."""

    def __init__(
        self,
        provider_type: ProviderType,
        chat_model: BaseChatModel,
        embeddings: Optional[Embeddings] = None,
        model_name: str = "unknown"
    ):
        self.provider_type = provider_type
        self.chat = chat_model
        self._embeddings = embeddings
        self.model_name = model_name

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_embeddings(self) -> bool:
        return self._embeddings is not None

    def invoke(self, prompt: str, **kwargs) -> LLMResponse:
        """Synchronous LLM invocation."""
        response = self.chat.invoke(prompt, **kwargs)
        return LLMResponse(
            content=response.content,
            model=self.model_name,
            provider=self.provider_type,
            tokens_used=getattr(response, 'usage_metadata', {}).get('total_tokens')
        )

    async def ainvoke(self, prompt: str, **kwargs) -> LLMResponse:
        """Asynchronous LLM invocation."""
        response = await self.chat.ainvoke(prompt, **kwargs)
        return LLMResponse(
            content=response.content,
            model=self.model_name,
            provider=self.provider_type
        )

    async def astream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream response tokens asynchronously."""
        async for chunk in self.chat.astream(prompt, **kwargs):
            if chunk.content:
                yield chunk.content

    def embed(self, texts: list[str]) -> EmbeddingResponse:
        """Generate embeddings for texts."""
        if not self._embeddings:
            raise NotImplementedError(
                f"Embeddings not available for {self.provider_type}"
            )
        vectors = self._embeddings.embed_documents(texts)
        return EmbeddingResponse(
            embeddings=vectors,
            model=self.model_name,
            dimensions=len(vectors[0]) if vectors else 0
        )

    def health_check(self) -> bool:
        """Check if the provider is available."""
        try:
            self.invoke("Hello")
            return True
        except Exception:
            return False
```

## Provider Registry

```python
# providers/registry.py

from typing import Optional, Dict, Type, Callable
from .base import LLMBoxProvider, ProviderType


class ProviderRegistry:
    """Factory for creating and caching provider instances."""

    _factories: Dict[ProviderType, Callable[..., LLMBoxProvider]] = {}
    _instances: Dict[str, LLMBoxProvider] = {}

    @classmethod
    def register(cls, provider_type: ProviderType):
        """Decorator to register a provider factory."""
        def decorator(factory: Callable[..., LLMBoxProvider]):
            cls._factories[provider_type] = factory
            return factory
        return decorator

    @classmethod
    def get(
        cls,
        provider_type: ProviderType,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMBoxProvider:
        """Get or create a provider instance."""
        # Cache key includes type and model
        cache_key = f"{provider_type.value}:{model or 'default'}"

        if cache_key not in cls._instances:
            factory = cls._factories.get(provider_type)
            if not factory:
                raise ValueError(f"Unknown provider: {provider_type}")
            cls._instances[cache_key] = factory(model=model, **kwargs)

        return cls._instances[cache_key]

    @classmethod
    def list_available(cls) -> list[ProviderType]:
        """List all registered providers."""
        return list(cls._factories.keys())

    @classmethod
    def clear_cache(cls):
        """Clear the instance cache."""
        cls._instances.clear()
```

## Provider Implementations

### Ollama Provider

```python
# providers/ollama.py

from typing import Optional
from langchain_ollama import ChatOllama, OllamaEmbeddings
from .base import LLMBoxProvider, ProviderType
from .registry import ProviderRegistry


@ProviderRegistry.register(ProviderType.OLLAMA)
def create_ollama_provider(
    model: str = "llama3",
    base_url: str = "http://localhost:11434",
    timeout: float = 120.0,
    **kwargs
) -> LLMBoxProvider:
    """Create an Ollama provider instance."""
    chat_model = ChatOllama(
        model=model,
        base_url=base_url,
        timeout=timeout,
        **kwargs
    )

    # Ollama supports embeddings with the same model
    embeddings = OllamaEmbeddings(
        model=model,
        base_url=base_url
    )

    return LLMBoxProvider(
        provider_type=ProviderType.OLLAMA,
        chat_model=chat_model,
        embeddings=embeddings,
        model_name=model
    )
```

### OpenAI Provider

```python
# providers/openai.py

from typing import Optional
import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from .base import LLMBoxProvider, ProviderType
from .registry import ProviderRegistry


@ProviderRegistry.register(ProviderType.OPENAI)
def create_openai_provider(
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
    embedding_model: str = "text-embedding-3-small",
    timeout: float = 60.0,
    **kwargs
) -> LLMBoxProvider:
    """Create an OpenAI provider instance."""
    api_key = api_key or os.environ.get("OPENAI_API_KEY")

    chat_model = ChatOpenAI(
        model=model,
        api_key=api_key,
        timeout=timeout,
        **kwargs
    )

    embeddings = OpenAIEmbeddings(
        model=embedding_model,
        api_key=api_key
    )

    return LLMBoxProvider(
        provider_type=ProviderType.OPENAI,
        chat_model=chat_model,
        embeddings=embeddings,
        model_name=model
    )
```

### Anthropic Provider

```python
# providers/anthropic.py

from typing import Optional
import os
from langchain_anthropic import ChatAnthropic
from .base import LLMBoxProvider, ProviderType
from .registry import ProviderRegistry


@ProviderRegistry.register(ProviderType.ANTHROPIC)
def create_anthropic_provider(
    model: str = "claude-sonnet-4-20250514",
    api_key: Optional[str] = None,
    max_tokens: int = 4096,
    timeout: float = 60.0,
    **kwargs
) -> LLMBoxProvider:
    """Create an Anthropic provider instance."""
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    chat_model = ChatAnthropic(
        model=model,
        api_key=api_key,
        max_tokens=max_tokens,
        timeout=timeout,
        **kwargs
    )

    # Anthropic doesn't have embeddings API
    # Use OpenAI embeddings as fallback if available
    embeddings = None
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        from langchain_openai import OpenAIEmbeddings
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=openai_key
        )

    return LLMBoxProvider(
        provider_type=ProviderType.ANTHROPIC,
        chat_model=chat_model,
        embeddings=embeddings,
        model_name=model
    )
```

### Mock Provider (for testing)

```python
# providers/mock.py

from typing import Dict, Optional
from .base import LLMBoxProvider, LLMResponse, EmbeddingResponse, ProviderType
from .registry import ProviderRegistry
import hashlib


class MockChatModel:
    """Mock chat model for testing."""

    def __init__(self, responses: Dict[str, str] = None):
        self.responses = responses or {}
        self.calls: list[str] = []

    def invoke(self, prompt: str, **kwargs):
        self.calls.append(prompt)

        # Check for predefined response
        for key, response in self.responses.items():
            if key.lower() in prompt.lower():
                return type('Response', (), {'content': response})()

        return type('Response', (), {'content': f"Mock response for: {prompt[:50]}..."})()

    async def ainvoke(self, prompt: str, **kwargs):
        return self.invoke(prompt, **kwargs)

    async def astream(self, prompt: str, **kwargs):
        response = self.invoke(prompt, **kwargs)
        for word in response.content.split():
            yield type('Chunk', (), {'content': word + ' '})()


class MockEmbeddings:
    """Mock embeddings for testing."""

    def __init__(self, dimensions: int = 128):
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate deterministic fake embeddings from text hash."""
        embeddings = []
        for text in texts:
            hash_bytes = hashlib.sha256(text.encode()).digest()
            # Create embedding from hash bytes, normalized to [-1, 1]
            embedding = [(b - 128) / 128.0 for b in hash_bytes[:self.dimensions]]
            embeddings.append(embedding)
        return embeddings


@ProviderRegistry.register(ProviderType.MOCK)
def create_mock_provider(
    model: str = "mock",
    responses: Dict[str, str] = None,
    embedding_dimensions: int = 128,
    **kwargs
) -> LLMBoxProvider:
    """Create a mock provider for testing."""
    chat_model = MockChatModel(responses=responses)
    embeddings = MockEmbeddings(dimensions=embedding_dimensions)

    return LLMBoxProvider(
        provider_type=ProviderType.MOCK,
        chat_model=chat_model,
        embeddings=embeddings,
        model_name=model
    )
```

## Retry Strategy

```python
# utils/retry.py

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from ..exceptions import ProviderRateLimitError


# Decorator for LLM calls with automatic retry
llm_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ProviderRateLimitError, ConnectionError)),
    reraise=True
)
```

## Fallback Strategy

```python
# providers/fallback.py

from typing import List
from .base import LLMBoxProvider, LLMResponse
from ..exceptions import ProviderError


def invoke_with_fallback(
    providers: List[LLMBoxProvider],
    prompt: str,
    **kwargs
) -> LLMResponse:
    """Try providers in order until one succeeds."""
    errors = []

    for provider in providers:
        try:
            return provider.invoke(prompt, **kwargs)
        except ProviderError as e:
            errors.append((provider.provider_type, str(e)))
            continue

    # All providers failed
    error_details = "; ".join(f"{p}: {e}" for p, e in errors)
    raise ProviderError(f"All providers failed: {error_details}")
```

## Configuration

### Provider Config Schema

```python
# config/schema.py

from pydantic import BaseModel, Field
from typing import Optional


class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""
    enabled: bool = True
    default_model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: float = 60.0
    extra: dict = Field(default_factory=dict)


class ProvidersConfig(BaseModel):
    """Configuration for all providers."""
    ollama: ProviderConfig = ProviderConfig(
        default_model="llama3",
        base_url="http://localhost:11434"
    )
    openai: ProviderConfig = ProviderConfig(
        enabled=False,
        default_model="gpt-4o-mini"
    )
    anthropic: ProviderConfig = ProviderConfig(
        enabled=False,
        default_model="claude-sonnet-4-20250514"
    )
```

### Example Config

```toml
# ~/.config/llm-box/config.toml

default_provider = "ollama"

[providers.ollama]
enabled = true
default_model = "llama3"
base_url = "http://localhost:11434"
timeout = 120.0

[providers.openai]
enabled = true
default_model = "gpt-4o-mini"
# api_key = ""  # Use OPENAI_API_KEY env var

[providers.anthropic]
enabled = true
default_model = "claude-sonnet-4-20250514"
# api_key = ""  # Use ANTHROPIC_API_KEY env var
```

## Usage Examples

### Basic Usage

```python
from llm_box.providers.registry import ProviderRegistry
from llm_box.providers.base import ProviderType

# Get default Ollama provider
provider = ProviderRegistry.get(ProviderType.OLLAMA)

# Invoke with specific model
provider = ProviderRegistry.get(ProviderType.OPENAI, model="gpt-4o")

# Generate text
response = provider.invoke("Explain this code: def foo(): pass")
print(response.content)

# Generate embeddings
embeddings = provider.embed(["file content here"])
print(f"Dimensions: {embeddings.dimensions}")
```

### Streaming

```python
import asyncio
from llm_box.providers.registry import ProviderRegistry
from llm_box.providers.base import ProviderType

async def stream_response():
    provider = ProviderRegistry.get(ProviderType.OLLAMA)

    async for token in provider.astream("Tell me a story"):
        print(token, end="", flush=True)

asyncio.run(stream_response())
```

### With Fallback

```python
from llm_box.providers.registry import ProviderRegistry
from llm_box.providers.base import ProviderType
from llm_box.providers.fallback import invoke_with_fallback

providers = [
    ProviderRegistry.get(ProviderType.OLLAMA),
    ProviderRegistry.get(ProviderType.OPENAI),
]

response = invoke_with_fallback(providers, "Summarize this file")
```

## See Also

- [architecture.md](./architecture.md) - Overall system architecture
- [caching.md](./caching.md) - How responses are cached
- [search.md](./search.md) - How embeddings are used for search
