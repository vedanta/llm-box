"""Tests for exception hierarchy."""

import pytest

from llm_box.exceptions import (
    CacheError,
    ConfigError,
    ConfigValidationError,
    LLMBoxError,
    ProviderAuthError,
    ProviderError,
    ProviderNotAvailableError,
    ProviderRateLimitError,
    SearchError,
)


class TestLLMBoxError:
    """Tests for base LLMBoxError."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = LLMBoxError()
        assert str(error) == "An error occurred"
        assert error.user_message == "An error occurred"
        assert error.exit_code == 1

    def test_custom_message(self) -> None:
        """Test custom error message."""
        error = LLMBoxError("Custom error")
        assert str(error) == "Custom error"

    def test_custom_user_message(self) -> None:
        """Test custom user message."""
        error = LLMBoxError("Internal", user_message="User-friendly message")
        assert error.user_message == "User-friendly message"


class TestProviderErrors:
    """Tests for provider-related errors."""

    def test_provider_error(self) -> None:
        """Test base provider error."""
        error = ProviderError()
        assert error.exit_code == 2
        assert "provider" in error.user_message.lower()

    def test_provider_not_available(self) -> None:
        """Test provider not available error."""
        error = ProviderNotAvailableError()
        assert "not available" in error.user_message.lower()

    def test_provider_rate_limit(self) -> None:
        """Test rate limit error."""
        error = ProviderRateLimitError()
        assert error.exit_code == 3
        assert "rate limit" in error.user_message.lower()

    def test_provider_auth_error(self) -> None:
        """Test auth error."""
        error = ProviderAuthError()
        assert error.exit_code == 4
        assert "authentication" in error.user_message.lower()


class TestCacheErrors:
    """Tests for cache-related errors."""

    def test_cache_error(self) -> None:
        """Test base cache error."""
        error = CacheError()
        assert error.exit_code == 10


class TestConfigErrors:
    """Tests for config-related errors."""

    def test_config_error(self) -> None:
        """Test base config error."""
        error = ConfigError()
        assert error.exit_code == 20

    def test_config_validation_error(self) -> None:
        """Test config validation error."""
        error = ConfigValidationError("Invalid value")
        assert error.exit_code == 22


class TestSearchErrors:
    """Tests for search-related errors."""

    def test_search_error(self) -> None:
        """Test base search error."""
        error = SearchError()
        assert error.exit_code == 30


class TestExceptionHierarchy:
    """Test exception inheritance."""

    def test_provider_inherits_from_base(self) -> None:
        """Test ProviderError inherits from LLMBoxError."""
        error = ProviderError()
        assert isinstance(error, LLMBoxError)

    def test_specific_provider_errors(self) -> None:
        """Test specific provider errors inherit correctly."""
        assert isinstance(ProviderNotAvailableError(), ProviderError)
        assert isinstance(ProviderRateLimitError(), ProviderError)
        assert isinstance(ProviderAuthError(), ProviderError)

    def test_can_catch_base_exception(self) -> None:
        """Test catching base exception catches all."""
        errors = [
            ProviderError(),
            CacheError(),
            ConfigError(),
            SearchError(),
        ]
        for error in errors:
            assert isinstance(error, LLMBoxError)
