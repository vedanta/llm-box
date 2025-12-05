"""Retry decorators and utilities using tenacity."""

from collections.abc import Callable
from typing import Any, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from llm_box.exceptions import (
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

F = TypeVar("F", bound=Callable[..., Any])


# Retry decorator for LLM calls
llm_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(
        (ProviderRateLimitError, ProviderTimeoutError, ConnectionError)
    ),
    reraise=True,
)
"""Retry decorator for LLM calls.

Retries up to 3 times with exponential backoff (1s, 2s, 4s)
for rate limits, timeouts, and connection errors.

Usage:
    @llm_retry
    def call_llm(prompt: str) -> str:
        return provider.invoke(prompt)
"""


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    retry_on: tuple[type[Exception], ...] = (
        ProviderRateLimitError,
        ProviderTimeoutError,
        ConnectionError,
    ),
) -> Callable[[F], F]:
    """Create a customized retry decorator.

    Args:
        max_attempts: Maximum number of retry attempts.
        min_wait: Minimum wait time between retries (seconds).
        max_wait: Maximum wait time between retries (seconds).
        retry_on: Tuple of exception types to retry on.

    Returns:
        A retry decorator with the specified configuration.

    Usage:
        @with_retry(max_attempts=5, min_wait=2.0)
        def call_llm(prompt: str) -> str:
            return provider.invoke(prompt)
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(retry_on),
        reraise=True,
    )


def retry_on_rate_limit(
    max_attempts: int = 5,
    min_wait: float = 1.0,
    max_wait: float = 60.0,
) -> Callable[[F], F]:
    """Retry decorator specifically for rate limit errors.

    Uses longer waits since rate limits typically require
    waiting longer before retrying.

    Args:
        max_attempts: Maximum number of retry attempts.
        min_wait: Minimum wait time between retries (seconds).
        max_wait: Maximum wait time between retries (seconds).

    Returns:
        A retry decorator configured for rate limits.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=2, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((ProviderRateLimitError,)),
        reraise=True,
    )


def retry_on_timeout(
    max_attempts: int = 3,
    min_wait: float = 0.5,
    max_wait: float = 5.0,
) -> Callable[[F], F]:
    """Retry decorator specifically for timeout errors.

    Uses shorter waits since timeouts are often transient.

    Args:
        max_attempts: Maximum number of retry attempts.
        min_wait: Minimum wait time between retries (seconds).
        max_wait: Maximum wait time between retries (seconds).

    Returns:
        A retry decorator configured for timeouts.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((ProviderTimeoutError, ConnectionError)),
        reraise=True,
    )


def retry_on_any_provider_error(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable[[F], F]:
    """Retry decorator for any provider error.

    Use with caution - this will retry on all provider errors,
    including authentication errors (which won't be fixed by retrying).

    Args:
        max_attempts: Maximum number of retry attempts.
        min_wait: Minimum wait time between retries (seconds).
        max_wait: Maximum wait time between retries (seconds).

    Returns:
        A retry decorator for all provider errors.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((ProviderError,)),
        reraise=True,
    )
