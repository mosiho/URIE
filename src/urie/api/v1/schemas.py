"""Pydantic request/response schemas for /v1."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    agent_id: str
    name: str = "Agent"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    agent_id: str


class DebriefCreateRequest(BaseModel):
    """
    Start a debrief.
    - mode=interview (default): opens a multi-turn gap-driven interview (transcript optional).
    - mode=oneshot: classic single-transcript ingest (transcript required).
    """

    transcript: Optional[str] = Field(
        None, description="Optional for interview mode; required for oneshot"
    )
    mode: str = Field(default="interview", pattern="^(interview|oneshot)$")


class DebriefTurnRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Agent's spoken/typed answer this turn")


class DebriefResolveRequest(BaseModel):
    resolution_note: str = Field(..., min_length=1)
    accepted_value: Optional[Any] = None
    resolved_node_id: Optional[str] = None
    # For ambiguity resolution:
    chosen_node_id: Optional[str] = None
    create_new: bool = False


class DebriefResponse(BaseModel):
    session_id: str
    agent_id: str
    status: str
    transcript: str = ""
    staged_mutations: List[Dict[str, Any]] = Field(default_factory=list)
    pending_challenge: Optional[Dict[str, Any]] = None
    turns: List[Dict[str, Any]] = Field(default_factory=list)
    covered_gaps: List[Any] = Field(default_factory=list)
    next_question: Optional[str] = None
    mode: str = "oneshot"
    created_at: Optional[str] = None


class NodeSummary(BaseModel):
    node_id: str
    kind: str
    name: str
    aliases: List[str] = Field(default_factory=list)
    attrs: Dict[str, Any] = Field(default_factory=dict)


class FeedItemResponse(BaseModel):
    feed_id: str
    agent_id: str
    subject_node_id: str
    script: str
    rationale: str
    gifting_suggestion: Optional[str] = None
    status: str
    held_until: Optional[str] = None
    source_event_id: Optional[str] = None
    created_at: Optional[str] = None


class FeedAckRequest(BaseModel):
    action: str = Field(default="acked", pattern="^(acked|dismissed)$")


class ConstraintCreateRequest(BaseModel):
    person_node_id: str
    label: str = "Do-Not-Disturb: high workload"
    window_start: Optional[str] = None
    window_end: Optional[str] = None


class CRMWritebackRequest(BaseModel):
    fact_id: str
    note: str
    crm_target: str = "stub"


class CRMWritebackResponse(BaseModel):
    writeback_id: str
    fact_id: str
    note: str
    crm_target: str
    idempotent_replay: bool = False
