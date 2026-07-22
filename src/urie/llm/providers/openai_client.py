"""OpenAI-compatible Chat Completions client (httpx)."""

from __future__ import annotations

import json
import time
from typing import Any, Optional

import httpx

from urie.llm.base import LLMClient, LLMRequest, LLMResponse, TokenUsage
from urie.llm.errors import LLMAuthError, LLMRateLimit, LLMTimeout, LLMUnavailable
from urie.llm.retry import with_retry


class OpenAICompatibleClient(LLMClient):
    """Works with OpenAI and any OpenAI-compatible gateway via base_url."""

    provider_name = "openai"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout_s: float = 45.0,
        max_retries: int = 3,
        default_temperature: float = 0.2,
    ) -> None:
        if not api_key:
            raise LLMAuthError("OpenAI API key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.default_temperature = default_temperature

    async def complete(self, request: LLMRequest) -> LLMResponse:
        async def _call() -> LLMResponse:
            return await self._complete_once(request)

        return await with_retry(_call, max_retries=self.max_retries)

    async def _complete_once(self, request: LLMRequest) -> LLMResponse:
        messages: list[dict[str, Any]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        for m in request.messages:
            messages.append(m.to_openai())

        if request.json_mode and request.response_schema_hint:
            # Nudge the model with the schema in a trailing system note
            messages.append(
                {
                    "role": "system",
                    "content": (
                        f"Respond with JSON only matching schema "
                        f"{request.response_schema_name}:\n{request.response_schema_hint}"
                    ),
                }
            )

        body: dict[str, Any] = {
            "model": request.model or self.model,
            "messages": messages,
            "temperature": request.temperature
            if request.temperature is not None
            else self.default_temperature,
            "max_tokens": request.max_tokens,
        }
        if request.json_mode:
            body["response_format"] = {"type": "json_object"}

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
        except httpx.TimeoutException as exc:
            raise LLMTimeout(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailable(str(exc)) from exc

        if resp.status_code == 401:
            raise LLMAuthError(resp.text)
        if resp.status_code == 429:
            retry_after = resp.headers.get("retry-after")
            raise LLMRateLimit(
                resp.text,
                retry_after_s=float(retry_after) if retry_after else None,
            )
        if resp.status_code >= 500:
            raise LLMUnavailable(resp.text)
        if resp.status_code >= 400:
            raise LLMUnavailable(f"HTTP {resp.status_code}: {resp.text}")

        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        text = ((choice.get("message") or {}).get("content")) or ""
        usage_raw = data.get("usage") or {}
        parsed: Optional[dict[str, Any]] = None
        if request.json_mode:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None

        return LLMResponse(
            text=text,
            parsed=parsed,
            usage=TokenUsage(
                prompt_tokens=int(usage_raw.get("prompt_tokens") or 0),
                completion_tokens=int(usage_raw.get("completion_tokens") or 0),
                total_tokens=int(usage_raw.get("total_tokens") or 0),
            ),
            latency_ms=(time.perf_counter() - t0) * 1000,
            model=data.get("model") or (request.model or self.model),
            finish_reason=choice.get("finish_reason"),
            provider=self.provider_name,
        )
