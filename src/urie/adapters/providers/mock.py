"""Deterministic mock STT / LLM / TTS / Embedder providers."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Optional, Sequence

from urie.config import get_settings
from urie.domain.challenge import CandidateMutation


class MockSTT:
    """Returns transcript_hint if provided; otherwise a fixed phrase."""

    async def transcribe(self, audio: bytes | None, transcript_hint: str | None = None) -> str:
        if transcript_hint:
            return transcript_hint
        return "Spoke with John about budget around five million."


class MockTTS:
    async def synthesize(self, text: str) -> bytes:
        return text.encode("utf-8")


class MockEmbedder:
    """Deterministic hash-based embedding of fixed dimension."""

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim or get_settings().embedding_dim

    async def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.lower().encode()).digest()
        # Expand digest into dim floats in [-1, 1]
        vals: list[float] = []
        i = 0
        while len(vals) < self.dim:
            b = digest[i % len(digest)]
            vals.append((b / 127.5) - 1.0)
            i += 1
            if i % len(digest) == 0:
                digest = hashlib.sha256(digest).digest()
        # L2 normalize
        norm = sum(v * v for v in vals) ** 0.5 or 1.0
        return [v / norm for v in vals]


class MockLLM:
    """
    Rule-based parser for canned debrief transcripts used in tests and demos.

    Recognizes patterns like:
      - "John's budget is 3 million" / "budget moved to 5 million"
      - "John's wife is expecting a baby"
      - "don't contact John until 2026-07-28" / "high workload"
    """

    async def parse_debrief(self, transcript: str, agent_id: str) -> list[CandidateMutation]:
        _ = agent_id
        text = transcript.strip()
        mutations: list[CandidateMutation] = []

        # Prefer possessive: "John's budget is 3 million"
        budget_m = re.search(
            r"(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'s\s+budget\b.*?"
            r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>million|billion|m|b)?",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if not budget_m:
            # "budget for John is 3 million" / "John — budget is 3 million"
            budget_m = re.search(
                r"\bbudget\b(?:\s+for)?\s+(?P<name>[A-Z][a-z]+).*?"
                r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>million|billion|m|b)?",
                text,
                re.IGNORECASE | re.DOTALL,
            )
        if not budget_m:
            budget_m = re.search(
                r"(?P<name>[A-Z][a-z]+).*?\bbudget\b.*?"
                r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>million|billion|m|b)?",
                text,
                re.IGNORECASE | re.DOTALL,
            )
            # Reject common false positives from sentence openers
            if budget_m and budget_m.group("name").lower() in {
                "met",
                "spoke",
                "update",
                "talked",
                "called",
                "saw",
                "great",
                "don",
            }:
                # Try to find a later capitalized person name before 'budget'
                alt = re.search(
                    r"\b(?P<name>[A-Z][a-z]+)'s\s+budget\b.*?"
                    r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>million|billion|m|b)?",
                    text,
                    re.IGNORECASE | re.DOTALL,
                )
                budget_m = alt
        if budget_m:
            name = budget_m.group("name").strip()
            amount = float(budget_m.group("amount"))
            unit = (budget_m.group("unit") or "").lower()
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
                CandidateMutation(
                    entity="Budget",
                    subject_node_id=None,
                    subject_spoken=name,
                    value={"amount": amount, "currency": currency},
                    is_hypothesis=hypothesis,
                )
            )

        # Life event / trait: expecting a baby
        baby_m = re.search(
            r"(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?).*?\b(expecting|pregnant|baby)\b",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if baby_m:
            name = baby_m.group("name").strip()
            # Avoid "John's wife" being the subject — prefer the primary name before possessive
            poss = re.search(
                r"(?P<name>[A-Z][a-z]+)'s\s+\w+.*?\b(expecting|pregnant|baby)\b",
                text,
                re.IGNORECASE,
            )
            if poss:
                name = poss.group("name").strip()
            mutations.append(
                CandidateMutation(
                    entity="LifeEvent",
                    subject_node_id=None,
                    subject_spoken=name,
                    value="expecting_a_baby",
                    is_hypothesis=False,
                    edge_type="HAS_TRAIT",
                    trait_name="Expecting a baby",
                )
            )

        # Constraint / DND
        dnd_m = re.search(
            r"(?:don'?t\s+contact|do\s*not\s+disturb|high\s+workload).*?"
            r"(?P<name>[A-Z][a-z]+).*?(?:until|through)\s+(?P<date>\d{4}-\d{2}-\d{2})",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if not dnd_m:
            dnd_m = re.search(
                r"(?P<name>[A-Z][a-z]+).*?(?:don'?t\s+contact|high\s+workload).*?"
                r"(?:until|through)\s+(?P<date>\d{4}-\d{2}-\d{2})",
                text,
                re.IGNORECASE | re.DOTALL,
            )
        if dnd_m:
            mutations.append(
                CandidateMutation(
                    entity="Constraint",
                    subject_node_id=None,
                    subject_spoken=dnd_m.group("name").strip(),
                    value={
                        "label": "Do-Not-Disturb: high workload",
                        "window_end": dnd_m.group("date"),
                    },
                    edge_type="CONSTRAINED_BY",
                    trait_name="Do-Not-Disturb: high workload",
                )
            )

        # Fallback: mention of a person with a freeform note
        if not mutations:
            person_m = re.search(r"\b(?:with|about|met)\s+([A-Z][a-z]+)\b", text)
            if person_m:
                mutations.append(
                    CandidateMutation(
                        entity="Note",
                        subject_node_id=None,
                        subject_spoken=person_m.group(1),
                        value=text[:500],
                        is_hypothesis=False,
                    )
                )

        return mutations

    async def synthesize_ghost_script(
        self,
        subject_name: str,
        trait_summary: str,
        context: dict[str, Any],
    ) -> tuple[str, str, Optional[str]]:
        _ = context
        script = (
            f"Call {subject_name} — their situation just shifted ({trait_summary}). "
            f"Open with a personal reference so they feel remembered."
        )
        rationale = f"Graph mutation: {trait_summary} on {subject_name}."
        gift = None
        if "baby" in trait_summary.lower() or "expecting" in trait_summary.lower():
            gift = "Consider a thoughtful small gift for the nursery — agent executes, not the system."
        return script, rationale, gift

    async def plan_interview(
        self,
        gaps: Sequence[Any],
        recent_turns: Sequence[dict[str, Any]],
        context: dict[str, Any] | None = None,
        *,
        turn_index: int = 0,
        max_turns: int | None = None,
    ) -> Any:
        """Deterministic interview planner (no network)."""
        from urie.llm.schemas import InterviewPlan

        _ = recent_turns, context
        max_t = max_turns if max_turns is not None else 8
        if turn_index >= max_t:
            return InterviewPlan(
                next_question="", target_gap=None, done=True, reason="max turns"
            )
        gap_list = list(gaps)
        if not gap_list:
            if turn_index == 0:
                return InterviewPlan(
                    next_question="What happened today with your clients — anyone worth remembering?",
                    target_gap=None,
                    done=False,
                    reason="empty opening",
                )
            return InterviewPlan(
                next_question="", target_gap=None, done=True, reason="no gaps"
            )
        top = gap_list[0]
        if hasattr(top, "to_dict"):
            top = top.to_dict()
        gtype = top.get("gap_type", "")
        name = top.get("subject_name") or "them"
        entity = top.get("entity") or "that detail"
        q = f"Anything new on {name}'s {entity}?"
        if gtype == "missing_attribute":
            q = f"Quick one on {name} — do you know their {entity.lower()} yet?"
        elif gtype == "stale_fact":
            q = f"Has anything shifted with {name}'s {entity.lower()} since we last talked?"
        elif gtype == "open_hypothesis":
            q = f"You weren't sure about {name}'s {entity.lower()} — any confirmation since?"
        elif gtype == "expired_constraint":
            q = f"{name}'s quiet period should be over — worth a check-in?"
        return InterviewPlan(
            next_question=q,
            target_gap=top.get("gap_id"),
            done=False,
            reason=top.get("rationale") or gtype,
        )


class ScriptedLLM(MockLLM):
    """LLM that returns pre-scripted mutations keyed by transcript substring."""

    def __init__(self, scripts: dict[str, list[CandidateMutation]] | None = None) -> None:
        self.scripts = scripts or {}

    async def parse_debrief(self, transcript: str, agent_id: str) -> list[CandidateMutation]:
        for key, mutations in self.scripts.items():
            if key.lower() in transcript.lower():
                return list(mutations)
        return await super().parse_debrief(transcript, agent_id)


def mutations_to_json(mutations: list[CandidateMutation]) -> str:
    return json.dumps(
        [
            {
                "entity": m.entity,
                "subject_spoken": m.subject_spoken,
                "value": m.value,
                "is_hypothesis": m.is_hypothesis,
                "edge_type": m.edge_type,
                "trait_name": m.trait_name,
            }
            for m in mutations
        ],
        default=str,
    )
