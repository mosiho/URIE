"""PromptedLLM — LLMPort implementation over any LLMClient."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from urie.config import get_settings
from urie.domain.challenge import CandidateMutation
from urie.domain.interview import KnowledgeGap
from urie.llm.base import LLMClient, LLMRequest
from urie.llm.factory import get_llm_client
from urie.llm.messages import Message
from urie.llm.prompts import challenge as challenge_prompt
from urie.llm.prompts import extraction as extraction_prompt
from urie.llm.prompts import ghost as ghost_prompt
from urie.llm.prompts import interview as interview_prompt
from urie.llm.schemas import ChallengePhrasing, ExtractionResult, GhostScript, InterviewPlan


class PromptedLLM:
    """
    High-level LLM operations for URIE, backed by a provider-agnostic LLMClient.
    Implements the extended LLMPort surface.
    """

    def __init__(self, client: LLMClient | None = None) -> None:
        self.client = client or get_llm_client()
        self.settings = get_settings()

    async def parse_debrief(self, transcript: str, agent_id: str) -> list[CandidateMutation]:
        _ = agent_id
        return await self.extract(transcript, context={})

    async def extract(
        self,
        turn_text: str,
        *,
        context: dict[str, Any] | None = None,
        known_people: list[str] | None = None,
    ) -> list[CandidateMutation]:
        user = extraction_prompt.render_extraction_user(
            turn_text, known_people=known_people, recent_context=context
        )
        req = LLMRequest(
            system=extraction_prompt.SYSTEM,
            messages=[Message.user(user)],
            temperature=self.settings.llm_temperature,
            json_mode=True,
            response_schema_name="ExtractionResult",
        )
        result = await self.client.complete_structured(req, ExtractionResult)
        return [_to_candidate(m) for m in result.mutations]

    async def synthesize_ghost_script(
        self,
        subject_name: str,
        trait_summary: str,
        context: dict[str, Any],
    ) -> tuple[str, str, Optional[str]]:
        user = ghost_prompt.render_ghost_user(subject_name, trait_summary, context)
        req = LLMRequest(
            system=ghost_prompt.SYSTEM,
            messages=[Message.user(user)],
            temperature=min(0.5, self.settings.llm_temperature + 0.15),
            json_mode=True,
            response_schema_name="GhostScript",
        )
        result = await self.client.complete_structured(req, GhostScript)
        return result.script, result.rationale, result.gifting_suggestion

    async def plan_interview(
        self,
        gaps: Sequence[KnowledgeGap] | Sequence[dict[str, Any]],
        recent_turns: Sequence[dict[str, Any]],
        context: dict[str, Any] | None = None,
        *,
        turn_index: int = 0,
        max_turns: int | None = None,
    ) -> InterviewPlan:
        gap_dicts = [
            g.to_dict() if isinstance(g, KnowledgeGap) else dict(g) for g in gaps
        ]
        max_t = max_turns if max_turns is not None else self.settings.llm_max_interview_turns
        user = interview_prompt.render_interview_user(
            gaps=gap_dicts,
            recent_turns=list(recent_turns),
            context=context,
            max_turns=max_t,
            turn_index=turn_index,
        )
        req = LLMRequest(
            system=interview_prompt.SYSTEM,
            messages=[Message.user(user)],
            temperature=self.settings.llm_temperature,
            json_mode=True,
            response_schema_name="InterviewPlan",
        )
        return await self.client.complete_structured(req, InterviewPlan)

    async def phrase_challenge(
        self,
        *,
        subject_spoken: str,
        entity: str,
        existing_value: Any,
        candidate_value: Any,
    ) -> ChallengePhrasing:
        user = challenge_prompt.render_challenge_user(
            subject_spoken=subject_spoken,
            entity=entity,
            existing_value=existing_value,
            candidate_value=candidate_value,
        )
        req = LLMRequest(
            system=challenge_prompt.SYSTEM,
            messages=[Message.user(user)],
            temperature=0.3,
            json_mode=True,
            response_schema_name="ChallengePhrasing",
        )
        return await self.client.complete_structured(req, ChallengePhrasing)


def _to_candidate(m) -> CandidateMutation:
    return CandidateMutation(
        entity=m.entity,
        subject_node_id=None,
        subject_spoken=m.subject_spoken,
        value=m.value,
        is_hypothesis=m.is_hypothesis,
        edge_type=m.edge_type,
        trait_name=m.trait_name,
        rel_label=m.rel_label,
    )
