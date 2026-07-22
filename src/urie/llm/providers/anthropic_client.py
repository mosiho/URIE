"""Anthropic Messages API client (httpx)."""

from __future__ import annotations

import json
import time
from typing import Any, Optional

import httpx

from urie.llm.base import LLMClient, LLMRequest, LLMResponse, TokenUsage
from urie.llm.errors import LLMAuthError, LLMRateLimit, LLMTimeout, LLMUnavailable
from urie.llm.retry import with_retry


class AnthropicClient(LLMClient):
    provider_name = "anthropic"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.anthropic.com",
        model: str = "claude-sonnet-4-20250514",
        timeout_s: float = 45.0,
        max_retries: int = 3,
        default_temperature: float = 0.2,
        api_version: str = "2023-06-01",
    ) -> None:
        if not api_key:
            raise LLMAuthError("Anthropic API key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.default_temperature = default_temperature
        self.api_version = api_version

    async def complete(self, request: LLMRequest) -> LLMResponse:
        async def _call() -> LLMResponse:
            return await self._complete_once(request)

        return await with_retry(_call, max_retries=self.max_retries)

    async def _complete_once(self, request: LLMRequest) -> LLMResponse:
        system = request.system or ""
        if request.json_mode and request.response_schema_hint:
            system += (
                f"\n\nRespond with JSON only matching schema "
                f"{request.response_schema_name}:\n{request.response_schema_hint}"
            )

        messages: list[dict[str, Any]] = []
        for m in request.messages:
            converted = m.to_anthropic()
            if converted:
                messages.append(converted)
        if not messages:
            messages = [{"role": "user", "content": "Proceed."}]

        body: dict[str, Any] = {
            "model": request.model or self.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature
            if request.temperature is not None
            else self.default_temperature,
            "messages": messages,
        }
        if system:
            body["system"] = system

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": self.api_version,
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
        blocks = data.get("content") or []
        text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
        text = "\n".join(text_parts)
        usage_raw = data.get("usage") or {}
        parsed: Optional[dict[str, Any]] = None
        if request.json_mode:
            raw = text.strip()
            if raw.startswith("```"):
                lines = [ln for ln in raw.split("\n") if not ln.strip().startswith("```")]
                raw = "\n".join(lines).strip()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None

        return LLMResponse(
            text=text,
            parsed=parsed,
            usage=TokenUsage(
                prompt_tokens=int(usage_raw.get("input_tokens") or 0),
                completion_tokens=int(usage_raw.get("output_tokens") or 0),
                total_tokens=int(usage_raw.get("input_tokens") or 0)
                + int(usage_raw.get("output_tokens") or 0),
            ),
            latency_ms=(time.perf_counter() - t0) * 1000,
            model=data.get("model") or (request.model or self.model),
            finish_reason=data.get("stop_reason"),
            provider=self.provider_name,
        )
