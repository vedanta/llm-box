"""Unit tests for LLM providers."""

import pytest

from llm_box.exceptions import ProviderNotAvailableError
from llm_box.providers import (
    EmbeddingResponse,
    FallbackProvider,
    LLMResponse,
    ProviderRegistry,
    ProviderType,
    embed_with_fallback,
    invoke_with_fallback,
)
from llm_box.providers.mock import MockProvider


class TestProviderType:
    """Tests for ProviderType enum."""

    def test_provider_types_exist(self) -> None:
        """Test that all expected provider types exist."""
        assert ProviderType.OLLAMA == "ollama"
        assert ProviderType.OPENAI == "openai"
        assert ProviderType.ANTHROPIC == "anthropic"
        assert ProviderType.MOCK == "mock"

    def test_provider_type_values(self) -> None:
        """Test provider type string values."""
        assert ProviderType.OLLAMA.value == "ollama"
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.ANTHROPIC.value == "anthropic"
        assert ProviderType.MOCK.value == "mock"


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_create_response(self) -> None:
        """Test creating an LLM response."""
        response = LLMResponse(
            content="Hello, world!",
            model="test-model",
            provider=ProviderType.MOCK,
        )
        assert response.content == "Hello, world!"
        assert response.model == "test-model"
        assert response.provider == ProviderType.MOCK
        assert response.tokens_used is None
        assert response.finish_reason is None
        assert response.metadata == {}

    def test_create_response_with_all_fields(self) -> None:
        """Test creating a response with all fields populated."""
        response = LLMResponse(
            content="Test content",
            model="gpt-4",
            provider=ProviderType.OPENAI,
            tokens_used=150,
            finish_reason="stop",
            metadata={"usage": {"prompt_tokens": 50, "completion_tokens": 100}},
        )
        assert response.tokens_used == 150
        assert response.finish_reason == "stop"
        assert response.metadata["usage"]["prompt_tokens"] == 50


class TestEmbeddingResponse:
    """Tests for EmbeddingResponse dataclass."""

    def test_create_embedding_response(self) -> None:
        """Test creating an embedding response."""
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        response = EmbeddingResponse(
            embeddings=embeddings,
            model="text-embedding-3-small",
            provider=ProviderType.OPENAI,
            dimensions=3,
        )
        assert response.embeddings == embeddings
        assert response.model == "text-embedding-3-small"
        assert response.dimensions == 3
        assert response.tokens_used is None


class TestMockProvider:
    """Tests for MockProvider."""

    def test_create_mock_provider(self) -> None:
        """Test creating a mock provider."""
        provider = MockProvider()
        assert provider.provider_type == ProviderType.MOCK
        assert provider.model_name == "mock-model"
        assert provider.supports_streaming is True
        assert provider.supports_embeddings is True

    def test_create_mock_provider_with_custom_model(self) -> None:
        """Test creating a mock provider with custom model name."""
        provider = MockProvider(model="custom-model")
        assert provider.model_name == "custom-model"

    def test_invoke_returns_deterministic_response(self) -> None:
        """Test that invoke returns deterministic responses."""
        provider = MockProvider()
        response1 = provider.invoke("Hello, world!")
        response2 = provider.invoke("Hello, world!")
        assert response1.content == response2.content

    def test_invoke_different_prompts_different_responses(self) -> None:
        """Test that different prompts get different responses."""
        provider = MockProvider()
        response1 = provider.invoke("Hello")
        response2 = provider.invoke("Goodbye")
        assert response1.content != response2.content

    def test_invoke_with_custom_responses(self) -> None:
        """Test invoke with custom response mapping."""
        provider = MockProvider(
            responses={
                "hello": "Hi there!",
                "weather": "It's sunny today.",
            }
        )
        response = provider.invoke("Hello, how are you?")
        assert response.content == "Hi there!"

        response = provider.invoke("What's the weather like?")
        assert response.content == "It's sunny today."

    def test_invoke_response_fields(self) -> None:
        """Test that invoke returns properly formatted response."""
        provider = MockProvider(model="test-model")
        response = provider.invoke("Test prompt")

        assert isinstance(response, LLMResponse)
        assert response.model == "test-model"
        assert response.provider == ProviderType.MOCK
        assert response.tokens_used is not None
        assert response.finish_reason == "stop"

    def test_call_history_tracking(self) -> None:
        """Test that calls are tracked in history."""
        provider = MockProvider()
        assert provider.call_count == 0

        provider.invoke("First call")
        assert provider.call_count == 1

        provider.invoke("Second call")
        assert provider.call_count == 2

        history = provider.call_history
        assert len(history) == 2
        assert history[0]["method"] == "invoke"
        assert history[0]["prompt"] == "First call"
        assert history[1]["prompt"] == "Second call"

    def test_clear_history(self) -> None:
        """Test clearing call history."""
        provider = MockProvider()
        provider.invoke("Test")
        assert provider.call_count == 1

        provider.clear_history()
        assert provider.call_count == 0
        assert provider.call_history == []

    def test_embed_returns_embeddings(self) -> None:
        """Test embedding generation."""
        provider = MockProvider(embedding_dimensions=64)
        response = provider.embed(["text1", "text2"])

        assert isinstance(response, EmbeddingResponse)
        assert len(response.embeddings) == 2
        assert len(response.embeddings[0]) == 64
        assert len(response.embeddings[1]) == 64
        assert response.dimensions == 64
        assert response.provider == ProviderType.MOCK

    def test_embed_deterministic(self) -> None:
        """Test that embeddings are deterministic."""
        provider = MockProvider()
        response1 = provider.embed(["same text"])
        response2 = provider.embed(["same text"])
        assert response1.embeddings == response2.embeddings

    def test_embed_different_texts_different_embeddings(self) -> None:
        """Test that different texts get different embeddings."""
        provider = MockProvider()
        response = provider.embed(["text one", "text two"])
        assert response.embeddings[0] != response.embeddings[1]

    @pytest.mark.asyncio
    async def test_ainvoke(self) -> None:
        """Test async invoke."""
        provider = MockProvider()
        response = await provider.ainvoke("Async test")

        assert isinstance(response, LLMResponse)
        assert "Async test" in response.content or "hash:" in response.content
        assert provider.call_count == 1
        assert provider.call_history[0]["method"] == "ainvoke"

    @pytest.mark.asyncio
    async def test_astream(self) -> None:
        """Test async streaming."""
        provider = MockProvider()
        chunks = []
        async for chunk in provider.astream("Stream test"):
            chunks.append(chunk)

        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response) > 0
        assert provider.call_count == 1
        assert provider.call_history[0]["method"] == "astream"

    def test_health_check(self) -> None:
        """Test health check always returns True for mock."""
        provider = MockProvider()
        assert provider.health_check() is True

    @pytest.mark.asyncio
    async def test_ahealth_check(self) -> None:
        """Test async health check."""
        provider = MockProvider()
        assert await provider.ahealth_check() is True


class TestProviderRegistry:
    """Tests for ProviderRegistry."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset registry cache between tests."""
        ProviderRegistry.clear_cache()

    def test_mock_provider_is_registered(self) -> None:
        """Test that mock provider is automatically registered."""
        assert ProviderRegistry.is_registered(ProviderType.MOCK)

    def test_list_available_includes_mock(self) -> None:
        """Test that mock is in available providers."""
        available = ProviderRegistry.list_available()
        assert ProviderType.MOCK in available

    def test_get_mock_provider(self) -> None:
        """Test getting a mock provider through registry."""
        provider = ProviderRegistry.get(ProviderType.MOCK)
        assert isinstance(provider, MockProvider)
        assert provider.provider_type == ProviderType.MOCK

    def test_get_mock_provider_with_model(self) -> None:
        """Test getting mock provider with specific model."""
        provider = ProviderRegistry.get(ProviderType.MOCK, model="custom")
        assert provider.model_name == "custom"

    def test_provider_caching(self) -> None:
        """Test that providers are cached by default."""
        provider1 = ProviderRegistry.get(ProviderType.MOCK, model="test")
        provider2 = ProviderRegistry.get(ProviderType.MOCK, model="test")
        assert provider1 is provider2

    def test_provider_no_cache(self) -> None:
        """Test bypassing provider cache."""
        provider1 = ProviderRegistry.get(ProviderType.MOCK, use_cache=False)
        provider2 = ProviderRegistry.get(ProviderType.MOCK, use_cache=False)
        assert provider1 is not provider2

    def test_different_models_different_instances(self) -> None:
        """Test that different models create different instances."""
        provider1 = ProviderRegistry.get(ProviderType.MOCK, model="model1")
        provider2 = ProviderRegistry.get(ProviderType.MOCK, model="model2")
        assert provider1 is not provider2

    def test_clear_cache(self) -> None:
        """Test clearing the provider cache."""
        ProviderRegistry.get(ProviderType.MOCK, model="test")
        assert ProviderRegistry.get_cached_count() > 0

        ProviderRegistry.clear_cache()
        assert ProviderRegistry.get_cached_count() == 0

    def test_unregistered_provider_raises_error(self) -> None:
        """Test that getting unregistered provider raises error."""
        # Save current factories
        saved_factories = ProviderRegistry._factories.copy()

        try:
            # Clear factories to simulate unregistered state
            ProviderRegistry.clear_factories()
            with pytest.raises(ProviderNotAvailableError) as exc_info:
                ProviderRegistry.get(ProviderType.MOCK)
            assert "not registered" in str(exc_info.value)
        finally:
            # Restore factories
            ProviderRegistry._factories = saved_factories

    def test_get_with_custom_kwargs(self) -> None:
        """Test getting provider with custom kwargs."""
        provider = ProviderRegistry.get(
            ProviderType.MOCK,
            model="test",
            embedding_dimensions=256,
        )
        # Verify the kwarg was passed
        response = provider.embed(["test"])
        assert response.dimensions == 256


class TestFallbackLogic:
    """Tests for multi-provider fallback."""

    def test_invoke_with_fallback_first_succeeds(self) -> None:
        """Test fallback when first provider succeeds."""
        provider1 = MockProvider(responses={"test": "Response from provider 1"})
        provider2 = MockProvider(responses={"test": "Response from provider 2"})

        response = invoke_with_fallback([provider1, provider2], "test prompt")

        assert response.content == "Response from provider 1"
        assert provider1.call_count == 1
        assert provider2.call_count == 0

    def test_invoke_with_fallback_empty_list_raises(self) -> None:
        """Test that empty provider list raises error."""
        with pytest.raises(ValueError) as exc_info:
            invoke_with_fallback([], "test")
        assert "At least one provider" in str(exc_info.value)

    def test_embed_with_fallback_first_succeeds(self) -> None:
        """Test embed fallback when first provider succeeds."""
        provider1 = MockProvider()
        provider2 = MockProvider()

        response = embed_with_fallback([provider1, provider2], ["test text"])

        assert len(response.embeddings) == 1
        assert provider1.call_count == 1
        assert provider2.call_count == 0

    def test_embed_with_fallback_empty_list_raises(self) -> None:
        """Test that empty provider list raises error."""
        with pytest.raises(ValueError) as exc_info:
            embed_with_fallback([], ["test"])
        assert "At least one provider" in str(exc_info.value)


class TestFallbackProvider:
    """Tests for FallbackProvider class."""

    def test_create_fallback_provider(self) -> None:
        """Test creating a fallback provider."""
        provider1 = MockProvider(model="primary")
        provider2 = MockProvider(model="secondary")

        fallback = FallbackProvider([provider1, provider2])

        assert fallback.provider_type == ProviderType.MOCK  # Uses MOCK as placeholder
        assert fallback.primary_provider is provider1

    def test_fallback_provider_empty_list_raises(self) -> None:
        """Test that empty provider list raises error."""
        with pytest.raises(ValueError) as exc_info:
            FallbackProvider([])
        assert "At least one provider" in str(exc_info.value)

    def test_fallback_invoke(self) -> None:
        """Test invoking through fallback provider."""
        provider1 = MockProvider(responses={"hello": "Hi from primary"})
        fallback = FallbackProvider([provider1])

        response = fallback.invoke("hello")
        assert response.content == "Hi from primary"

    @pytest.mark.asyncio
    async def test_fallback_ainvoke(self) -> None:
        """Test async invoke through fallback provider."""
        provider1 = MockProvider(responses={"async": "Async response"})
        fallback = FallbackProvider([provider1])

        response = await fallback.ainvoke("async test")
        assert "Async response" in response.content or "hash:" in response.content

    def test_fallback_supports_streaming_is_false(self) -> None:
        """Test that fallback provider doesn't support streaming."""
        provider = MockProvider()
        fallback = FallbackProvider([provider])
        assert fallback.supports_streaming is False

    def test_fallback_supports_embeddings(self) -> None:
        """Test that fallback reports embeddings support based on providers."""
        provider_with_embeddings = MockProvider()
        assert provider_with_embeddings.supports_embeddings is True

        fallback = FallbackProvider([provider_with_embeddings])
        assert fallback.supports_embeddings is True

    def test_fallback_embed(self) -> None:
        """Test embedding through fallback provider."""
        provider = MockProvider(embedding_dimensions=32)
        fallback = FallbackProvider([provider])

        response = fallback.embed(["test text"])
        assert len(response.embeddings) == 1
        assert len(response.embeddings[0]) == 32

    def test_fallback_repr(self) -> None:
        """Test string representation of fallback provider."""
        provider1 = MockProvider()
        provider2 = MockProvider()
        fallback = FallbackProvider([provider1, provider2])

        repr_str = repr(fallback)
        assert "FallbackProvider" in repr_str
        assert "mock" in repr_str
