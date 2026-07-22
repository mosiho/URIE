"""Async retry with exponential backoff for LLM calls."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from urie.llm.errors import LLMError, LLMRateLimit, LLMTimeout, LLMUnavailable

T = TypeVar("T")


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 3,
    base_delay_s: float = 0.5,
    max_delay_s: float = 8.0,
    retryable: tuple[type[Exception], ...] = (LLMTimeout, LLMRateLimit, LLMUnavailable),
) -> T:
    """
    Retry `fn` on transient LLM errors with exponential backoff + jitter.
    Honors LLMRateLimit.retry_after_s when present.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except retryable as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            delay = min(max_delay_s, base_delay_s * (2**attempt))
            if isinstance(exc, LLMRateLimit) and exc.retry_after_s:
                delay = max(delay, float(exc.retry_after_s))
            delay *= 0.5 + random.random()  # jitter
            await asyncio.sleep(delay)
        except LLMError:
            raise
    assert last_exc is not None
    raise last_exc
