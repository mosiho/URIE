"""Ports (Protocols) — I/O boundaries for hexagonal architecture."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Protocol, Sequence, runtime_checkable

from urie.domain.challenge import CandidateMutation
from urie.domain.entity_resolution import CandidateNode, ERWeights
from urie.domain.facts import Fact
from urie.domain.reasoning import ActiveConstraint


@runtime_checkable
class STTPort(Protocol):
    async def transcribe(self, audio: bytes | None, transcript_hint: str | None = None) -> str: ...


@runtime_checkable
class LLMPort(Protocol):
    async def parse_debrief(self, transcript: str, agent_id: str) -> list[CandidateMutation]: ...

    async def synthesize_ghost_script(
        self,
        subject_name: str,
        trait_summary: str,
        context: dict[str, Any],
    ) -> tuple[str, str, Optional[str]]:
        """Returns (script, rationale, gifting_suggestion)."""
        ...

    async def plan_interview(
        self,
        gaps: Sequence[Any],
        recent_turns: Sequence[dict[str, Any]],
        context: dict[str, Any] | None = None,
        *,
        turn_index: int = 0,
        max_turns: int | None = None,
    ) -> Any:
        """Return an InterviewPlan-like object with next_question / done / reason."""
        ...


@runtime_checkable
class TTSPort(Protocol):
    async def synthesize(self, text: str) -> bytes: ...


@runtime_checkable
class EmbedderPort(Protocol):
    async def embed(self, text: str) -> list[float]: ...


@runtime_checkable
class FactRepository(Protocol):
    async def get_active(self, agent_id: str, subject_node_id: str, entity: str) -> Optional[Fact]: ...

    async def save(self, fact: Fact) -> Fact: ...

    async def mark_superseded(self, old_fact_id: str, new_fact_id: str) -> None: ...

    async def list_for_subject(self, agent_id: str, subject_node_id: str) -> list[Fact]: ...


@runtime_checkable
class GraphRepository(Protocol):
    async def get_node(self, agent_id: str, node_id: str) -> Optional[dict[str, Any]]: ...

    async def find_person_candidates(self, agent_id: str, spoken: str) -> list[CandidateNode]: ...

    async def create_node(
        self,
        agent_id: str,
        kind: str,
        name: str,
        aliases: list[str] | None = None,
        attrs: dict | None = None,
        node_id: str | None = None,
    ) -> str: ...

    async def touch_node(self, agent_id: str, node_id: str) -> None: ...

    async def upsert_edge(
        self,
        agent_id: str,
        edge_type: str,
        src_node_id: str,
        dst_node_id: str,
        fact_id: str | None = None,
        confidence: float = 0.8,
        rel_label: str | None = None,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
        attrs: dict | None = None,
    ) -> str: ...

    async def neighbor_ids(self, agent_id: str, node_id: str) -> set[str]: ...

    async def active_constraints(self, agent_id: str, person_node_id: str) -> list[ActiveConstraint]: ...

    async def depth2_context(self, agent_id: str, node_id: str) -> dict[str, Any]: ...

    async def list_nodes(self, agent_id: str, kind: str | None = None) -> list[dict[str, Any]]: ...

    async def get_er_weights(self, agent_id: str) -> ERWeights: ...


@runtime_checkable
class EmbeddingRepository(Protocol):
    async def upsert(self, agent_id: str, node_id: str, embedding: Sequence[float]) -> None: ...

    async def search(
        self, agent_id: str, embedding: Sequence[float], limit: int = 10
    ) -> list[tuple[str, float]]: ...


@runtime_checkable
class EventBus(Protocol):
    async def publish(self, agent_id: str, event_type: str, payload: dict[str, Any]) -> str: ...

    async def poll_unprocessed(self, limit: int = 50) -> list[dict[str, Any]]: ...

    async def mark_processed(self, event_id: str) -> None: ...
