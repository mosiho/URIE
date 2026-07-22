"""/v1 API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from urie.adapters.db import models as m
from urie.adapters.db.repositories import PostgresEmbeddingRepository, PostgresGraphRepository
from urie.adapters.db.session import get_session
from urie.adapters.providers.mock import MockEmbedder
from urie.api.deps import AgentPrincipal, create_access_token, get_agent_session, get_current_agent
from urie.api.v1.schemas import (
    CRMWritebackRequest,
    CRMWritebackResponse,
    ConstraintCreateRequest,
    DebriefCreateRequest,
    DebriefResolveRequest,
    DebriefResponse,
    DebriefTurnRequest,
    FeedAckRequest,
    FeedItemResponse,
    NodeSummary,
    TokenRequest,
    TokenResponse,
)
from urie.adapters.providers.prompted import PromptedLLM
from urie.services.ingestion import IngestionService
from urie.services.interview import InterviewService
from urie.services.reasoning_worker import ConstraintService, FeedService, ReasoningWorker

api_router = APIRouter()


# ── Auth (dev) ──────────────────────────────────────────────────────────────


@api_router.post("/auth/token", response_model=TokenResponse, tags=["auth"])
async def mint_token(
    body: TokenRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    svc = IngestionService(session)
    await svc.ensure_agent(body.agent_id, body.name)
    await session.commit()
    token = create_access_token(body.agent_id, body.name)
    return TokenResponse(access_token=token, agent_id=body.agent_id)


# ── Debriefs ────────────────────────────────────────────────────────────────


@api_router.post("/debriefs", response_model=DebriefResponse, tags=["debriefs"])
async def start_debrief(
    body: DebriefCreateRequest,
    agent: Annotated[AgentPrincipal, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_agent_session)],
) -> DebriefResponse:
    # Multi-turn interview (default) — or oneshot when transcript + mode=oneshot
    if body.mode == "oneshot":
        if not body.transcript:
            raise HTTPException(status_code=400, detail="transcript required for oneshot mode")
        svc = IngestionService(session, llm=PromptedLLM())
        result = await svc.start_debrief(agent.agent_id, transcript=body.transcript)
        worker = ReasoningWorker(session, llm=PromptedLLM())
        await worker.process_pending()
        return DebriefResponse(**result)

    # Interview mode: optional seed transcript as first user turn after opening Q
    interview = InterviewService(session)
    result = await interview.start_interview(agent.agent_id, agent.name or "Agent")
    if body.transcript and body.transcript.strip():
        result = await interview.submit_turn(agent.agent_id, result["session_id"], body.transcript)
    return DebriefResponse(**result)


@api_router.post("/debriefs/{session_id}/turn", response_model=DebriefResponse, tags=["debriefs"])
async def debrief_turn(
    session_id: str,
    body: DebriefTurnRequest,
    agent: Annotated[AgentPrincipal, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_agent_session)],
) -> DebriefResponse:
    interview = InterviewService(session)
    try:
        result = await interview.submit_turn(agent.agent_id, session_id, body.text)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DebriefResponse(**result)


@api_router.post("/debriefs/{session_id}/finish", response_model=DebriefResponse, tags=["debriefs"])
async def finish_debrief(
    session_id: str,
    agent: Annotated[AgentPrincipal, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_agent_session)],
) -> DebriefResponse:
    interview = InterviewService(session)
    try:
        result = await interview.finish(agent.agent_id, session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DebriefResponse(**result)


@api_router.get("/debriefs/{session_id}", response_model=DebriefResponse, tags=["debriefs"])
async def get_debrief(
    session_id: str,
    agent: Annotated[AgentPrincipal, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_agent_session)],
) -> DebriefResponse:
    svc = IngestionService(session)
    try:
        result = await svc.get_debrief(agent.agent_id, session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DebriefResponse(**result)


@api_router.post("/debriefs/{session_id}/resolve", response_model=DebriefResponse, tags=["debriefs"])
async def resolve_debrief(
    session_id: str,
    body: DebriefResolveRequest,
    agent: Annotated[AgentPrincipal, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_agent_session)],
) -> DebriefResponse:
    svc = IngestionService(session, llm=PromptedLLM())
    try:
        current = await svc.get_debrief(agent.agent_id, session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pending = current.get("pending_challenge") or {}
    try:
        if pending.get("type") == "ambiguity":
            result = await svc.resolve_ambiguity(
                agent.agent_id,
                session_id,
                chosen_node_id=body.chosen_node_id or body.resolved_node_id,
                create_new=body.create_new,
            )
        else:
            result = await svc.resolve_challenge(
                agent.agent_id,
                session_id,
                resolution_note=body.resolution_note,
                accepted_value=body.accepted_value,
                resolved_node_id=body.resolved_node_id,
            )
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    worker = ReasoningWorker(session, llm=PromptedLLM())
    await worker.process_pending()

    # Resume interview planning after a challenge resolution
    if (current.get("mode") or result.get("mode")) == "interview":
        interview = InterviewService(session)
        # Force status back to interviewing and ask for next question via empty-gap plan
        # by submitting a synthetic continuation (recompute gaps only):
        try:
            row = await interview._get_row(agent.agent_id, session_id)
            row.status = m.DebriefStatus.INTERVIEWING
            await session.flush()
            gaps = await interview._current_gaps(agent.agent_id)
            covered = set(row.covered_gaps or [])
            open_gaps = [g for g in gaps if g.gap_id not in covered]
            turns = list(row.turns or [])
            user_turns = sum(1 for t in turns if t.get("role") == "user")
            plan = await interview.llm.plan_interview(
                open_gaps,
                recent_turns=turns,
                context={"agent_id": agent.agent_id},
                turn_index=user_turns,
            )
            if plan.done or not plan.next_question:
                row.status = m.DebriefStatus.COMPLETED
                row.next_question = None
            else:
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
            await session.flush()
            await session.commit()
            result = await interview.get_session(agent.agent_id, session_id)
        except Exception:
            pass  # fall through with resolve result

    return DebriefResponse(**result)


# ── Nodes ───────────────────────────────────────────────────────────────────


@api_router.get("/nodes", tags=["nodes"])
async def list_nodes(
    agent: Annotated[AgentPrincipal, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_agent_session)],
    q: Optional[str] = Query(None, description="Semantic / name search"),
    kind: Optional[str] = None,
) -> list[dict[str, Any]]:
    graph = PostgresGraphRepository(session)
    if q:
        embedder = MockEmbedder()
        emb_repo = PostgresEmbeddingRepository(session)
        vec = await embedder.embed(q)
        hits = await emb_repo.search(agent.agent_id, vec, limit=20)
        results = []
        for node_id, distance in hits:
            node = await graph.get_node(agent.agent_id, node_id)
            if node and (kind is None or node["kind"] == kind):
                results.append({**node, "distance": distance})
        # Also fall back to name substring if vector empty
        if not results:
            all_nodes = await graph.list_nodes(agent.agent_id, kind=kind)
            ql = q.lower()
            results = [
                n
                for n in all_nodes
                if ql in n["name"].lower() or any(ql in a.lower() for a in n.get("aliases", []))
            ]
        return results
    return await graph.list_nodes(agent.agent_id, kind=kind)


@api_router.get("/nodes/{node_id}", tags=["nodes"])
async def get_node(
    node_id: str,
    agent: Annotated[AgentPrincipal, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_agent_session)],
) -> dict[str, Any]:
    graph = PostgresGraphRepository(session)
    node = await graph.get_node(agent.agent_id, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    from urie.adapters.db.repositories import PostgresFactRepository

    facts = PostgresFactRepository(session)
    fact_list = await facts.list_for_subject(agent.agent_id, node_id)
    constraints = await graph.active_constraints(agent.agent_id, node_id)
    return {
        **node,
        "facts": [
            {
                "fact_id": f.fact_id,
                "entity": f.entity,
                "value": f.value,
                "confidence_score": f.confidence_score,
                "is_hypothesis": f.is_hypothesis,
                "is_conflict_resolution": f.is_conflict_resolution,
                "superseded_by": f.superseded_by,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in fact_list
        ],
        "constraints": [
            {
                "edge_id": c.edge_id,
                "label": c.label,
                "window_end": c.window_end.isoformat() if c.window_end else None,
            }
            for c in constraints
        ],
    }


@api_router.get("/nodes/{node_id}/context", tags=["nodes"])
async def get_node_context(
    node_id: str,
    agent: Annotated[AgentPrincipal, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_agent_session)],
) -> dict[str, Any]:
    graph = PostgresGraphRepository(session)
    ctx = await graph.depth2_context(agent.agent_id, node_id)
    if not ctx.get("node"):
        raise HTTPException(status_code=404, detail="Node not found")
    return ctx


# ── Feed ────────────────────────────────────────────────────────────────────


@api_router.get("/feed", response_model=list[FeedItemResponse], tags=["feed"])
async def get_feed(
    agent: Annotated[AgentPrincipal, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_agent_session)],
    include_held: bool = False,
) -> list[FeedItemResponse]:
    # Process any pending outbox first
    worker = ReasoningWorker(session)
    await worker.process_pending()
    svc = FeedService(session)
    items = await svc.list_feed(agent.agent_id, include_held=include_held)
    return [FeedItemResponse(**i) for i in items]


@api_router.post("/feed/{feed_id}/ack", response_model=FeedItemResponse, tags=["feed"])
async def ack_feed(
    feed_id: str,
    body: FeedAckRequest,
    agent: Annotated[AgentPrincipal, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_agent_session)],
) -> FeedItemResponse:
    svc = FeedService(session)
    try:
        item = await svc.ack(agent.agent_id, feed_id, action=body.action)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FeedItemResponse(**item)


# ── Constraints ─────────────────────────────────────────────────────────────


@api_router.get("/constraints", tags=["constraints"])
async def list_constraints(
    agent: Annotated[AgentPrincipal, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_agent_session)],
    person_node_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    svc = ConstraintService(session)
    return await svc.list_constraints(agent.agent_id, person_node_id)


@api_router.post("/constraints", tags=["constraints"])
async def create_constraint(
    body: ConstraintCreateRequest,
    agent: Annotated[AgentPrincipal, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_agent_session)],
) -> dict[str, Any]:
    svc = ConstraintService(session)

    def _parse(dt: str | None) -> datetime | None:
        if not dt:
            return None
        d = datetime.fromisoformat(dt)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d

    try:
        return await svc.set_constraint(
            agent.agent_id,
            body.person_node_id,
            body.label,
            window_start=_parse(body.window_start),
            window_end=_parse(body.window_end),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── CRM write-back ──────────────────────────────────────────────────────────


@api_router.post("/crm/writeback", response_model=CRMWritebackResponse, tags=["crm"])
async def crm_writeback(
    body: CRMWritebackRequest,
    agent: Annotated[AgentPrincipal, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_agent_session)],
) -> CRMWritebackResponse:
    # Idempotent on fact_id
    existing = (
        await session.execute(select(m.CRMWriteback).where(m.CRMWriteback.fact_id == body.fact_id))
    ).scalar_one_or_none()
    if existing:
        if existing.agent_id != agent.agent_id:
            raise HTTPException(status_code=403, detail="Fact belongs to another agent")
        return CRMWritebackResponse(
            writeback_id=existing.writeback_id,
            fact_id=existing.fact_id,
            note=existing.note,
            crm_target=existing.crm_target,
            idempotent_replay=True,
        )

    # Verify fact exists and is scoped
    fact = (
        await session.execute(
            select(m.Fact).where(
                m.Fact.fact_id == body.fact_id, m.Fact.agent_id == agent.agent_id
            )
        )
    ).scalar_one_or_none()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")

    wb_id = f"wb_{uuid4()}"
    row = m.CRMWriteback(
        writeback_id=wb_id,
        agent_id=agent.agent_id,
        fact_id=body.fact_id,
        note=body.note,
        crm_target=body.crm_target,
    )
    session.add(row)
    await session.commit()
    return CRMWritebackResponse(
        writeback_id=wb_id,
        fact_id=body.fact_id,
        note=body.note,
        crm_target=body.crm_target,
        idempotent_replay=False,
    )


# ── Health ──────────────────────────────────────────────────────────────────


@api_router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
