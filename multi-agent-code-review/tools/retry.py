"""Retry strategies with exponential backoff and circuit breaker.

Based on Codex tool orchestration patterns:
- Exponential backoff for transient failures
- Circuit breaker for cascading failures
- Jitter to prevent thundering herd
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar


T = TypeVar("T")


class RetryStrategy(Enum):
    """Retry strategy types."""
    NONE = "none"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIBONACCI = "fibonacci"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: float = 0.1  # 0-1, fraction of delay to randomize
    retriable_exceptions: tuple = (Exception,)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"    # Normal operation
    OPEN = "open"        # Failing, reject requests
    HALF_OPEN = "half"  # Testing if recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5      # Failures before opening
    success_threshold: int = 2      # Successes to close
    timeout: float = 30.0           # Seconds before half-open
    excluded_exceptions: tuple = () # Exceptions that don't count


class CircuitBreaker:
    """
    Circuit breaker for preventing cascading failures.

    States:
    - CLOSED: Normal operation
    - OPEN: Failing, reject requests
    - HALF_OPEN: Testing recovery
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        if self._state == CircuitState.OPEN:
            # Check if timeout has passed
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.timeout:
                    self._state = CircuitState.HALF_OPEN
        return self._state

    def is_allowed(self) -> bool:
        """Check if request is allowed."""
        return self.state != CircuitState.OPEN

    def record_success(self):
        """Record a successful call."""
        self._failure_count = 0
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._success_count = 0

    def record_failure(self, exception: Exception):
        """Record a failed call."""
        # Check if exception is excluded
        if isinstance(exception, self.config.excluded_exceptions):
            return

        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._success_count = 0
        elif self._failure_count >= self.config.failure_threshold:
            self._state = CircuitState.OPEN

    def reset(self):
        """Reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None


def calculate_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """
    Calculate delay for retry attempt.

    Args:
        attempt: Attempt number (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    if config.strategy == RetryStrategy.LINEAR:
        delay = config.base_delay * (attempt + 1)
    elif config.strategy == RetryStrategy.FIBONACCI:
        # Fibonacci sequence
        a, b = 1, 1
        for _ in range(attempt):
            a, b = b, a + b
        delay = config.base_delay * a
    else:  # EXPONENTIAL
        delay = config.base_delay * (2 ** attempt)

    # Add jitter
    if config.jitter > 0:
        jitter_range = delay * config.jitter
        delay += random.uniform(-jitter_range, jitter_range)

    # Clamp to max
    return min(delay, config.max_delay)


async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
    **kwargs,
) -> T:
    """
    Execute function with retry logic.

    Args:
        func: Async function to execute
        *args: Function arguments
        config: Retry configuration
        circuit_breaker: Optional circuit breaker
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        Last exception if all retries exhausted
    """
    config = config or RetryConfig()
    last_exception: Optional[Exception] = None

    for attempt in range(config.max_retries + 1):
        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.is_allowed():
            raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)

            if circuit_breaker:
                circuit_breaker.record_success()

            return result

        except config.retriable_exceptions as e:
            last_exception = e

            if circuit_breaker:
                circuit_breaker.record_failure(e)

            # Don't delay on last attempt
            if attempt < config.max_retries:
                delay = calculate_delay(attempt, config)
                await asyncio.sleep(delay)

    raise last_exception


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
):
    """
    Decorator for adding retry logic to async functions.

    Args:
        config: Retry configuration
        circuit_breaker: Optional circuit breaker

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(
                func, *args,
                config=config,
                circuit_breaker=circuit_breaker,
                **kwargs,
            )
        return wrapper
    return decorator
