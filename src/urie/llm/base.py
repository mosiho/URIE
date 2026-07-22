"""LLM request/response types and client ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel, Field

from urie.llm.messages import Message

T = TypeVar("T", bound=BaseModel)


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMRequest(BaseModel):
    """Normalized completion request across providers."""

    system: Optional[str] = None
    messages: list[Message] = Field(default_factory=list)
    temperature: float = 0.2
    max_tokens: int = 2048
    model: Optional[str] = None  # override default model
    # When set, providers should ask for JSON matching this schema name / description
    response_schema_name: Optional[str] = None
    response_schema_hint: Optional[str] = None  # JSON Schema string or description
    json_mode: bool = False


class LLMResponse(BaseModel):
    text: str
    parsed: Optional[dict[str, Any]] = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    model: str = ""
    finish_reason: Optional[str] = None
    provider: str = ""


class LLMClient(ABC):
    """Provider-agnostic LLM client."""

    provider_name: str = "base"

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Free-text (or JSON-mode) completion."""

    async def complete_structured(self, request: LLMRequest, schema: Type[T]) -> T:
        """
        Complete and parse into a Pydantic model.
        Default: force json_mode, parse text as JSON, validate against schema.
        Providers may override for native structured-output APIs.
        """
        import json

        from urie.llm.errors import LLMParseError

        req = request.model_copy(
            update={
                "json_mode": True,
                "response_schema_name": schema.__name__,
                "response_schema_hint": json.dumps(schema.model_json_schema()),
            }
        )
        resp = await self.complete(req)
        raw = resp.parsed
        if raw is None:
            text = resp.text.strip()
            # Strip markdown fences if present
            if text.startswith("```"):
                lines = text.split("\n")
                lines = [ln for ln in lines if not ln.strip().startswith("```")]
                text = "\n".join(lines).strip()
            try:
                raw = json.loads(text)
            except json.JSONDecodeError as exc:
                raise LLMParseError(f"Invalid JSON from model: {exc}\n---\n{text[:500]}") from exc
        try:
            return schema.model_validate(raw)
        except Exception as exc:
            raise LLMParseError(f"Schema validation failed for {schema.__name__}: {exc}") from exc
