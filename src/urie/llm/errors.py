"""LLM error hierarchy."""

from __future__ import annotations


class LLMError(Exception):
    """Base LLM failure."""


class LLMTimeout(LLMError):
    """Provider timed out."""


class LLMRateLimit(LLMError):
    """Provider rate-limited the request."""

    def __init__(self, message: str = "rate limited", retry_after_s: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_s = retry_after_s


class LLMParseError(LLMError):
    """Failed to parse structured output from the model."""


class LLMAuthError(LLMError):
    """Invalid or missing API credentials."""


class LLMUnavailable(LLMError):
    """Provider returned a 5xx / connection failure."""
