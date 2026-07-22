"""Deterministic MockLLMClient — default offline provider."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from urie.llm.base import LLMClient, LLMRequest, LLMResponse, TokenUsage
from urie.llm.schemas import (
    ChallengePhrasing,
    ExtractionResult,
    ExtractedMutation,
    GhostScript,
    InterviewPlan,
)


class MockLLMClient(LLMClient):
    """
    Returns valid structured JSON without calling a network.
    Used for tests, demos, and zero-config local runs.
    """

    provider_name = "mock"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        t0 = time.perf_counter()
        schema = (request.response_schema_name or "").lower()
        user_blob = " ".join(m.content for m in request.messages)

        if "extraction" in schema or "ExtractionResult" in (request.response_schema_name or ""):
            payload = self._extract(user_blob)
        elif "interview" in schema or "InterviewPlan" in (request.response_schema_name or ""):
            payload = self._interview(user_blob)
        elif "ghost" in schema or "GhostScript" in (request.response_schema_name or ""):
            payload = self._ghost(user_blob)
        elif "challenge" in schema or "ChallengePhrasing" in (request.response_schema_name or ""):
            payload = self._challenge(user_blob)
        else:
            # Heuristic from system prompt keywords
            sys = (request.system or "").lower()
            if "extract" in sys:
                payload = self._extract(user_blob)
            elif "interview" in sys or "next question" in sys:
                payload = self._interview(user_blob)
            elif "ghost" in sys:
                payload = self._ghost(user_blob)
            elif "contradict" in sys or "challenge" in sys:
                payload = self._challenge(user_blob)
            else:
                payload = {"ok": True, "echo": user_blob[:200]}

        text = json.dumps(payload)
        return LLMResponse(
            text=text,
            parsed=payload,
            usage=TokenUsage(prompt_tokens=50, completion_tokens=80, total_tokens=130),
            latency_ms=(time.perf_counter() - t0) * 1000,
            model="mock-v1",
            finish_reason="stop",
            provider=self.provider_name,
        )

    def _extract(self, blob: str) -> dict[str, Any]:
        # Pull the agent turn between quotes if present
        m = re.search(r'"""(.*?)"""', blob, re.DOTALL)
        text = m.group(1).strip() if m else blob
        mutations: list[dict[str, Any]] = []

        budget = re.search(
            r"(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'s\s+budget\b.*?"
            r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>million|billion|m|b)?",
            text,
            re.I | re.DOTALL,
        )
        if not budget:
            budget = re.search(
                r"\b(?P<name>[A-Z][a-z]+)'s\s+budget\b.*?(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>million|billion|m|b)?",
                text,
                re.I | re.DOTALL,
            )
        if budget:
            amount = float(budget.group("amount"))
            unit = (budget.group("unit") or "").lower()
            if unit in ("million", "m"):
                amount *= 1_000_000
            elif unit in ("billion", "b"):
                amount *= 1_000_000_000
            currency = "USD"
            if re.search(r"\b(EUR|euro)\b", text, re.I):
                currency = "EUR"
            if re.search(r"\b(IRT|toman)\b", text, re.I):
                currency = "IRT"
            hypothesis = bool(re.search(r"\b(think|maybe|around|roughly)\b", text, re.I))
            mutations.append(
                ExtractedMutation(
                    entity="Budget",
                    subject_spoken=budget.group("name").strip(),
                    value={"amount": amount, "currency": currency},
                    is_hypothesis=hypothesis,
                    confidence=0.7 if hypothesis else 0.85,
                ).model_dump()
            )

        baby = re.search(
            r"(?P<name>[A-Z][a-z]+)'s\s+\w+.*?\b(expecting|pregnant|baby)\b",
            text,
            re.I,
        )
        if baby:
            mutations.append(
                ExtractedMutation(
                    entity="LifeEvent",
                    subject_spoken=baby.group("name").strip(),
                    value="expecting_a_baby",
                    edge_type="HAS_TRAIT",
                    trait_name="Expecting a baby",
                    confidence=0.9,
                ).model_dump()
            )

        dnd = re.search(
            r"(?:don'?t\s+contact|do\s*not\s+disturb|high\s+workload).*?"
            r"(?P<name>[A-Z][a-z]+).*?(?:until|through)\s+(?P<date>\d{4}-\d{2}-\d{2})",
            text,
            re.I | re.DOTALL,
        )
        if not dnd:
            dnd = re.search(
                r"(?P<name>[A-Z][a-z]+).*?(?:don'?t\s+contact|high\s+workload).*?"
                r"(?:until|through)\s+(?P<date>\d{4}-\d{2}-\d{2})",
                text,
                re.I | re.DOTALL,
            )
        if dnd:
            mutations.append(
                ExtractedMutation(
                    entity="Constraint",
                    subject_spoken=dnd.group("name").strip(),
                    value={
                        "label": "Do-Not-Disturb: high workload",
                        "window_end": dnd.group("date"),
                    },
                    edge_type="CONSTRAINED_BY",
                    trait_name="Do-Not-Disturb: high workload",
                    confidence=0.95,
                ).model_dump()
            )

        if not mutations:
            person = re.search(r"\b(?:with|about|met)\s+([A-Z][a-z]+)\b", text)
            if person:
                mutations.append(
                    ExtractedMutation(
                        entity="Note",
                        subject_spoken=person.group(1),
                        value=text[:500],
                    ).model_dump()
                )

        return ExtractionResult(
            mutations=[ExtractedMutation.model_validate(m) for m in mutations],
            summary=text[:120],
        ).model_dump()

    def _interview(self, blob: str) -> dict[str, Any]:
        # Parse gaps from the user message if present
        gaps: list[dict[str, Any]] = []
        gm = re.search(r"Open knowledge gaps.*?:\s*(\[.*?\])\s*\n", blob, re.S)
        if gm:
            try:
                gaps = json.loads(gm.group(1))
            except json.JSONDecodeError:
                gaps = []
        # Also try full JSON block
        if not gaps:
            jm = re.search(r"Open knowledge gaps.*?:\s*(\[[\s\S]*?\])\s*\n\n", blob)
            if jm:
                try:
                    gaps = json.loads(jm.group(1))
                except json.JSONDecodeError:
                    gaps = []

        turn_m = re.search(r"Turn index:\s*(\d+)\s*/\s*max\s*(\d+)", blob)
        turn_index = int(turn_m.group(1)) if turn_m else 0
        max_turns = int(turn_m.group(2)) if turn_m else 8

        if turn_index >= max_turns:
            return InterviewPlan(
                next_question="",
                target_gap=None,
                done=True,
                reason="max turns reached",
            ).model_dump()

        if not gaps:
            if turn_index == 0:
                return InterviewPlan(
                    next_question="What happened today with your clients — anyone worth remembering?",
                    target_gap=None,
                    done=False,
                    reason="empty graph opening",
                ).model_dump()
            return InterviewPlan(
                next_question="",
                target_gap=None,
                done=True,
                reason="no open gaps",
            ).model_dump()

        top = gaps[0]
        gtype = top.get("gap_type", "")
        name = top.get("subject_name") or top.get("subject_node_id") or "them"
        entity = top.get("entity") or "that detail"
        if gtype == "missing_attribute":
            q = f"Quick one on {name} — do you know their {entity.lower()} yet?"
        elif gtype == "stale_fact":
            q = f"Has anything shifted with {name}'s {entity.lower()} since we last talked?"
        elif gtype == "open_hypothesis":
            q = f"You weren't sure about {name}'s {entity.lower()} — any confirmation since?"
        elif gtype == "low_confidence":
            q = f"How confident are you now about {name}'s {entity.lower()}?"
        elif gtype == "expired_constraint":
            q = f"{name}'s quiet period should be over — worth a check-in?"
        else:
            q = f"Anything new on {name} I should lock in?"
        return InterviewPlan(
            next_question=q,
            target_gap=top.get("gap_id") or f"{gtype}:{entity}",
            done=False,
            reason=top.get("rationale") or gtype,
        ).model_dump()

    def _ghost(self, blob: str) -> dict[str, Any]:
        name_m = re.search(r"Subject:\s*(.+)", blob)
        trait_m = re.search(r"Trigger / trait:\s*(.+)", blob)
        name = name_m.group(1).strip() if name_m else "your client"
        trait = trait_m.group(1).strip() if trait_m else "a recent shift"
        gift = None
        if re.search(r"baby|expecting|nursery", trait, re.I):
            gift = "A small, thoughtful nursery gift — you deliver it; the system stays invisible."
        return GhostScript(
            script=(
                f"Call {name} — open by referencing {trait}. "
                f"Show you remembered the detail they mentioned in passing; keep it human and brief."
            ),
            rationale=f"Relationship moment: {trait} on {name}.",
            gifting_suggestion=gift,
        ).model_dump()

    def _challenge(self, blob: str) -> dict[str, Any]:
        subj = re.search(r"Subject:\s*(.+)", blob)
        ent = re.search(r"Entity:\s*(.+)", blob)
        name = subj.group(1).strip() if subj else "them"
        entity = ent.group(1).strip() if ent else "that"
        return ChallengePhrasing(
            vui_prompt=f"Interesting — {name}'s {entity} looks different from what we had. What shifted?",
            tone_note="curious colleague",
        ).model_dump()
