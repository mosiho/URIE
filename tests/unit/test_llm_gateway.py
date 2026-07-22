"""Unit tests for LLM gateway: mock client, prompts, retry, PromptedLLM."""

from __future__ import annotations

import pytest

from urie.llm.base import LLMRequest
from urie.llm.errors import LLMRateLimit, LLMTimeout
from urie.llm.factory import build_llm_client
from urie.llm.messages import Message
from urie.llm.prompts import extraction, interview
from urie.llm.providers.mock_client import MockLLMClient
from urie.llm.retry import with_retry
from urie.llm.schemas import ExtractionResult, InterviewPlan
from urie.adapters.providers.prompted import PromptedLLM


@pytest.mark.asyncio
async def test_mock_client_extracts_budget():
    client = MockLLMClient()
    req = LLMRequest(
        system=extraction.SYSTEM,
        messages=[
            Message.user(
                extraction.render_extraction_user(
                    "Met John. John's budget is 3 million USD."
                )
            )
        ],
        json_mode=True,
        response_schema_name="ExtractionResult",
    )
    result = await client.complete_structured(req, ExtractionResult)
    assert result.mutations
    assert result.mutations[0].entity == "Budget"
    assert result.mutations[0].subject_spoken == "John"


@pytest.mark.asyncio
async def test_mock_client_interview_opening():
    client = MockLLMClient()
    req = LLMRequest(
        system=interview.SYSTEM,
        messages=[
            Message.user(
                interview.render_interview_user(
                    gaps=[], recent_turns=[], turn_index=0, max_turns=8
                )
            )
        ],
        json_mode=True,
        response_schema_name="InterviewPlan",
    )
    plan = await client.complete_structured(req, InterviewPlan)
    assert plan.done is False
    assert "clients" in plan.next_question.lower() or "happened" in plan.next_question.lower()


@pytest.mark.asyncio
async def test_prompted_llm_extract_and_plan():
    llm = PromptedLLM(MockLLMClient())
    muts = await llm.extract("John's budget is 3 million.")
    assert any(m.entity == "Budget" for m in muts)

    plan = await llm.plan_interview([], [], turn_index=0)
    assert plan.next_question


@pytest.mark.asyncio
async def test_factory_defaults_to_mock():
    client = build_llm_client("openai", api_key="")  # no key → mock
    assert client.provider_name == "mock"


@pytest.mark.asyncio
async def test_retry_succeeds_after_rate_limit():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise LLMRateLimit("slow down", retry_after_s=0.01)
        return "ok"

    out = await with_retry(flaky, max_retries=3, base_delay_s=0.01)
    assert out == "ok"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_retry_exhausts():
    async def always_fail():
        raise LLMTimeout("nope")

    with pytest.raises(LLMTimeout):
        await with_retry(always_fail, max_retries=1, base_delay_s=0.01)


def test_prompt_renderers_include_context():
    u = extraction.render_extraction_user("hi", known_people=["John"])
    assert "John" in u
    assert "hi" in u
    i = interview.render_interview_user(
        gaps=[{"gap_type": "missing_attribute", "entity": "Budget", "subject_name": "John"}],
        recent_turns=[],
        turn_index=1,
    )
    assert "Budget" in i
