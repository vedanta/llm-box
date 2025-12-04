"""Unit tests for retry utilities."""

from unittest.mock import Mock

import pytest

from llm_box.exceptions import (
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from llm_box.utils.retry import (
    llm_retry,
    retry_on_any_provider_error,
    retry_on_rate_limit,
    retry_on_timeout,
    with_retry,
)


class TestLLMRetry:
    """Tests for the llm_retry decorator."""

    def test_llm_retry_success_no_retry(self) -> None:
        """Test that successful calls don't retry."""
        mock_func = Mock(return_value="success")
        decorated = llm_retry(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_llm_retry_on_rate_limit(self) -> None:
        """Test retry on rate limit error."""
        mock_func = Mock(
            side_effect=[
                ProviderRateLimitError("Rate limited"),
                "success",
            ]
        )
        decorated = llm_retry(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_llm_retry_on_timeout(self) -> None:
        """Test retry on timeout error."""
        mock_func = Mock(
            side_effect=[
                ProviderTimeoutError("Timeout"),
                "success",
            ]
        )
        decorated = llm_retry(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_llm_retry_on_connection_error(self) -> None:
        """Test retry on connection error."""
        mock_func = Mock(
            side_effect=[
                ConnectionError("Connection failed"),
                "success",
            ]
        )
        decorated = llm_retry(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_llm_retry_max_attempts_exceeded(self) -> None:
        """Test that max attempts are respected."""
        mock_func = Mock(side_effect=ProviderRateLimitError("Rate limited"))
        decorated = llm_retry(mock_func)

        with pytest.raises(ProviderRateLimitError):
            decorated()

        # llm_retry has 3 attempts
        assert mock_func.call_count == 3

    def test_llm_retry_non_retriable_error_not_retried(self) -> None:
        """Test that non-retriable errors are not retried."""
        mock_func = Mock(side_effect=ValueError("Bad value"))
        decorated = llm_retry(mock_func)

        with pytest.raises(ValueError):
            decorated()

        assert mock_func.call_count == 1


class TestWithRetry:
    """Tests for the with_retry factory."""

    def test_with_retry_custom_attempts(self) -> None:
        """Test custom max attempts."""
        mock_func = Mock(side_effect=ProviderRateLimitError("Rate limited"))

        @with_retry(max_attempts=5)
        def test_func() -> str:
            return mock_func()

        with pytest.raises(ProviderRateLimitError):
            test_func()

        assert mock_func.call_count == 5

    def test_with_retry_custom_exceptions(self) -> None:
        """Test retry on custom exception types."""
        mock_func = Mock(
            side_effect=[
                KeyError("Missing key"),
                "success",
            ]
        )

        @with_retry(retry_on=(KeyError,))
        def test_func() -> str:
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_with_retry_success_first_try(self) -> None:
        """Test successful call on first try."""
        mock_func = Mock(return_value="immediate success")

        @with_retry(max_attempts=3)
        def test_func() -> str:
            return mock_func()

        result = test_func()

        assert result == "immediate success"
        assert mock_func.call_count == 1


class TestRetryOnRateLimit:
    """Tests for retry_on_rate_limit decorator."""

    def test_retry_on_rate_limit_retries(self) -> None:
        """Test that rate limit errors are retried."""
        mock_func = Mock(
            side_effect=[
                ProviderRateLimitError("Rate limited"),
                ProviderRateLimitError("Still rate limited"),
                "success",
            ]
        )

        @retry_on_rate_limit(max_attempts=5)
        def test_func() -> str:
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_on_rate_limit_ignores_other_errors(self) -> None:
        """Test that non-rate-limit errors are not retried."""
        mock_func = Mock(side_effect=ProviderTimeoutError("Timeout"))

        @retry_on_rate_limit(max_attempts=5)
        def test_func() -> str:
            return mock_func()

        with pytest.raises(ProviderTimeoutError):
            test_func()

        assert mock_func.call_count == 1


class TestRetryOnTimeout:
    """Tests for retry_on_timeout decorator."""

    def test_retry_on_timeout_retries(self) -> None:
        """Test that timeout errors are retried."""
        mock_func = Mock(
            side_effect=[
                ProviderTimeoutError("Timeout"),
                "success",
            ]
        )

        @retry_on_timeout(max_attempts=3)
        def test_func() -> str:
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_on_timeout_retries_connection_error(self) -> None:
        """Test that connection errors are also retried."""
        mock_func = Mock(
            side_effect=[
                ConnectionError("Connection lost"),
                "success",
            ]
        )

        @retry_on_timeout(max_attempts=3)
        def test_func() -> str:
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_on_timeout_ignores_rate_limit(self) -> None:
        """Test that rate limit errors are not retried by timeout decorator."""
        mock_func = Mock(side_effect=ProviderRateLimitError("Rate limited"))

        @retry_on_timeout(max_attempts=3)
        def test_func() -> str:
            return mock_func()

        with pytest.raises(ProviderRateLimitError):
            test_func()

        assert mock_func.call_count == 1


class TestRetryOnAnyProviderError:
    """Tests for retry_on_any_provider_error decorator."""

    def test_retry_on_any_provider_error(self) -> None:
        """Test that any ProviderError is retried."""
        mock_func = Mock(
            side_effect=[
                ProviderError("Generic error"),
                "success",
            ]
        )

        @retry_on_any_provider_error(max_attempts=3)
        def test_func() -> str:
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_on_provider_subclasses(self) -> None:
        """Test that ProviderError subclasses are also retried."""
        mock_func = Mock(
            side_effect=[
                ProviderRateLimitError("Rate limited"),
                ProviderTimeoutError("Timeout"),
                "success",
            ]
        )

        @retry_on_any_provider_error(max_attempts=5)
        def test_func() -> str:
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_on_non_provider_error_not_retried(self) -> None:
        """Test that non-ProviderError is not retried."""
        mock_func = Mock(side_effect=RuntimeError("Runtime issue"))

        @retry_on_any_provider_error(max_attempts=3)
        def test_func() -> str:
            return mock_func()

        with pytest.raises(RuntimeError):
            test_func()

        assert mock_func.call_count == 1


class TestRetryWithArguments:
    """Tests for retry decorators preserving function arguments."""

    def test_llm_retry_preserves_args(self) -> None:
        """Test that arguments are passed correctly on retry."""
        call_args = []

        @llm_retry
        def test_func(a: int, b: str, c: float = 1.0) -> str:
            call_args.append((a, b, c))
            if len(call_args) < 2:
                raise ProviderTimeoutError("Timeout")
            return f"{a}-{b}-{c}"

        result = test_func(1, "test", c=2.5)

        assert result == "1-test-2.5"
        assert len(call_args) == 2
        assert call_args[0] == (1, "test", 2.5)
        assert call_args[1] == (1, "test", 2.5)
