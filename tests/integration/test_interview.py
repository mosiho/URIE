"""Integration: multi-turn gap-driven interview (Postgres)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from urie.adapters.providers.prompted import PromptedLLM
from urie.llm.providers.mock_client import MockLLMClient
from urie.services.ingestion import IngestionService
from urie.services.interview import InterviewService


@pytest.mark.asyncio
async def test_multi_turn_interview_flow(session: AsyncSession):
    llm = PromptedLLM(MockLLMClient())
    interview = InterviewService(session, llm=llm)

    opened = await interview.start_interview("agt_int", "Interview Agent")
    assert opened["status"] == "interviewing"
    assert opened["next_question"]
    assert opened["mode"] == "interview"
    sid = opened["session_id"]

    t1 = await interview.submit_turn(
        "agt_int",
        sid,
        "Met with John today. John's budget is 3 million USD.",
    )
    assert t1["status"] in ("interviewing", "completed")
    assert any(t.get("role") == "user" for t in t1["turns"])

    if t1["status"] == "interviewing":
        t2 = await interview.submit_turn(
            "agt_int",
            sid,
            "John's wife is expecting a baby.",
        )
        assert t2["status"] in ("interviewing", "completed", "awaiting_resolution")
        if t2["status"] == "interviewing":
            fin = await interview.finish("agt_int", sid)
            assert fin["status"] == "completed"
            assert fin["next_question"] is None

    # Contradiction oneshot still works alongside interviews
    oneshot = IngestionService(session, llm=llm)
    await oneshot.ensure_agent("agt_int", "Interview Agent")
    r = await oneshot.start_debrief(
        "agt_int",
        transcript="Update on John — John's budget is 5 million USD now.",
    )
    assert r["status"] == "awaiting_resolution"
    assert r.get("pending_challenge")

    resolved = await oneshot.resolve_challenge(
        "agt_int",
        r["session_id"],
        resolution_note="Bonus landed.",
        accepted_value={"amount": 5_000_000, "currency": "USD"},
    )
    assert resolved["status"] == "completed"
