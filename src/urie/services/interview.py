"""Multi-turn, gap-driven debrief interview orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from urie.adapters.db import models as m
from urie.adapters.db.repositories import PostgresFactRepository, PostgresGraphRepository
from urie.adapters.providers.prompted import PromptedLLM
from urie.config import get_settings
from urie.domain.interview import KnowledgeGap, detect_gaps
from urie.services.ingestion import IngestionService
from urie.services.reasoning_worker import ReasoningWorker


class InterviewService:
    """
    Opens a debrief with a gap-driven question, then iterates:
      agent answer → extract → mutation pipeline → recompute gaps → next question
    Bounded by llm_max_interview_turns (cost invariant).
    """

    def __init__(
        self,
        session: AsyncSession,
        llm: PromptedLLM | None = None,
    ) -> None:
        self.session = session
        self.llm = llm or PromptedLLM()
        self.ingestion = IngestionService(session, llm=self.llm)
        self.graph = PostgresGraphRepository(session)
        self.facts = PostgresFactRepository(session)
        self.settings = get_settings()

    async def start_interview(self, agent_id: str, agent_name: str = "Agent") -> dict[str, Any]:
        await self.ingestion.ensure_agent(agent_id, agent_name)
        gaps = await self._current_gaps(agent_id)
        plan = await self.llm.plan_interview(
            gaps,
            recent_turns=[],
            context={"agent_id": agent_id},
            turn_index=0,
            max_turns=self.settings.llm_max_interview_turns,
        )
        opening = plan.next_question or (
            "What happened today with your clients — anyone worth remembering?"
        )
        row = m.DebriefSession(
            session_id=f"deb_{uuid4()}",
            agent_id=agent_id,
            status=m.DebriefStatus.INTERVIEWING,
            transcript="",
            staged_mutations=[],
            pending_challenge=None,
            turns=[
                {
                    "role": "assistant",
                    "content": opening,
                    "at": datetime.now(timezone.utc).isoformat(),
                    "target_gap": plan.target_gap,
                }
            ],
            covered_gaps=[],
            next_question=opening,
            mode="interview",
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.commit()
        return await self.get_session(agent_id, row.session_id)

    async def submit_turn(
        self,
        agent_id: str,
        session_id: str,
        text: str,
    ) -> dict[str, Any]:
        row = await self._get_row(agent_id, session_id)
        if row.status not in (
            m.DebriefStatus.INTERVIEWING,
            m.DebriefStatus.ACTIVE,
            m.DebriefStatus.AWAITING_RESOLUTION,
        ):
            raise ValueError(f"Session {session_id} is not accepting turns (status={row.status})")

        # If a challenge is pending, caller should use /resolve instead
        if row.pending_challenge and row.status == m.DebriefStatus.AWAITING_RESOLUTION:
            raise ValueError("Resolve the pending challenge before submitting another turn")

        turns = list(row.turns or [])
        turns.append(
            {
                "role": "user",
                "content": text,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        row.turns = turns
        # Accumulate transcript for compatibility / search
        row.transcript = ((row.transcript or "") + "\n" + text).strip()
        await self.session.flush()

        # Extract mutations from this turn
        people = await self.graph.list_nodes(agent_id, kind="Person")
        known = [p["name"] for p in people]
        mutations = await self.llm.extract(
            text, context={"session_id": session_id}, known_people=known
        )

        # Reuse ingestion mutation pipeline (ER, challenge, write saga)
        result = await self.ingestion._process_mutations(row, mutations)

        # If challenge paused the session, return that state
        if result.get("status") == "awaiting_resolution":
            # Refresh row fields onto response
            return await self._enrich(agent_id, session_id)

        # Kick reasoning for any new events
        worker = ReasoningWorker(self.session, llm=self.llm)
        await worker.process_pending()

        # Recompute gaps and plan next question
        row = await self._get_row(agent_id, session_id)
        turns = list(row.turns or [])
        user_turn_count = sum(1 for t in turns if t.get("role") == "user")
        max_turns = self.settings.llm_max_interview_turns

        gaps = await self._current_gaps(agent_id)
        # Filter out already-covered gap ids
        covered = set(row.covered_gaps or [])
        open_gaps = [g for g in gaps if g.gap_id not in covered]

        plan = await self.llm.plan_interview(
            open_gaps,
            recent_turns=turns,
            context={"agent_id": agent_id},
            turn_index=user_turn_count,
            max_turns=max_turns,
        )

        if plan.done or user_turn_count >= max_turns or not plan.next_question:
            row.status = m.DebriefStatus.COMPLETED
            row.next_question = None
            await self.session.flush()
            await self.session.commit()
            return await self._enrich(agent_id, session_id)

        # Mark target gap covered when we ask about it
        if plan.target_gap:
            covered_list = list(row.covered_gaps or [])
            if plan.target_gap not in covered_list:
                covered_list.append(plan.target_gap)
                row.covered_gaps = covered_list

        turns.append(
            {
                "role": "assistant",
                "content": plan.next_question,
                "at": datetime.now(timezone.utc).isoformat(),
                "target_gap": plan.target_gap,
                "reason": plan.reason,
            }
        )
        row.turns = turns
        row.next_question = plan.next_question
        row.status = m.DebriefStatus.INTERVIEWING
        await self.session.flush()
        await self.session.commit()
        return await self._enrich(agent_id, session_id)

    async def finish(self, agent_id: str, session_id: str) -> dict[str, Any]:
        row = await self._get_row(agent_id, session_id)
        row.status = m.DebriefStatus.COMPLETED
        row.next_question = None
        await self.session.flush()
        await self.session.commit()
        worker = ReasoningWorker(self.session, llm=self.llm)
        await worker.process_pending()
        return await self._enrich(agent_id, session_id)

    async def get_session(self, agent_id: str, session_id: str) -> dict[str, Any]:
        return await self._enrich(agent_id, session_id)

    async def _enrich(self, agent_id: str, session_id: str) -> dict[str, Any]:
        row = await self._get_row(agent_id, session_id)
        return {
            "session_id": row.session_id,
            "agent_id": row.agent_id,
            "status": row.status.value if hasattr(row.status, "value") else row.status,
            "transcript": row.transcript or "",
            "staged_mutations": row.staged_mutations or [],
            "pending_challenge": row.pending_challenge,
            "turns": row.turns or [],
            "covered_gaps": row.covered_gaps or [],
            "next_question": row.next_question,
            "mode": row.mode or "oneshot",
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    async def _get_row(self, agent_id: str, session_id: str) -> m.DebriefSession:
        q = select(m.DebriefSession).where(
            m.DebriefSession.session_id == session_id,
            m.DebriefSession.agent_id == agent_id,
        )
        row = (await self.session.execute(q)).scalar_one_or_none()
        if not row:
            raise LookupError(f"Debrief session {session_id} not found")
        return row

    async def _current_gaps(self, agent_id: str) -> list[KnowledgeGap]:
        people = await self.graph.list_nodes(agent_id, kind="Person")
        all_facts = []
        for p in people:
            all_facts.extend(await self.facts.list_for_subject(agent_id, p["node_id"]))
        # Constraints across people
        constraints: list[dict[str, Any]] = []
        for p in people:
            for c in await self.graph.active_constraints(agent_id, p["node_id"]):
                constraints.append(
                    {
                        "subject_node_id": p["node_id"],
                        "label": c.label,
                        "window_end": c.window_end,
                        "window_start": c.window_start,
                    }
                )
        return detect_gaps(people=people, facts=all_facts, constraints=constraints)
