"""Pydantic structured-output schemas for LLM calls."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ExtractedMutation(BaseModel):
    """Mirrors domain CandidateMutation for structured extraction."""

    entity: str = Field(..., description="Fact/entity type, e.g. Budget, LifeEvent, Constraint, Note")
    subject_spoken: str = Field(..., description="Person name as spoken by the agent")
    value: Any = Field(..., description="Extracted value — scalar, money object, or structured dict")
    is_hypothesis: bool = False
    edge_type: Optional[str] = Field(
        None, description="HAS_TRAIT | CONSTRAINED_BY | RELATES_TO | DECIDES_FOR if applicable"
    )
    trait_name: Optional[str] = None
    rel_label: Optional[str] = None
    confidence: float = Field(0.85, ge=0.0, le=1.0)


class ExtractionResult(BaseModel):
    mutations: list[ExtractedMutation] = Field(default_factory=list)
    summary: str = Field("", description="One-sentence summary of what the agent said this turn")


class InterviewPlan(BaseModel):
    next_question: str = Field(..., description="The single next question to ask the agent")
    target_gap: Optional[str] = Field(
        None, description="Gap id or short label this question addresses, if any"
    )
    done: bool = Field(False, description="True when the interview should end")
    reason: str = Field("", description="Why this question / why done")


class GhostScript(BaseModel):
    script: str = Field(..., description="What the agent should say/do — they execute it themselves")
    rationale: str = Field(..., description="Why this moment / this detail matters")
    gifting_suggestion: Optional[str] = Field(
        None, description="Optional gift idea the agent executes (never the system)"
    )


class ChallengePhrasing(BaseModel):
    vui_prompt: str = Field(
        ...,
        description="Short spoken question asking why a fact changed — never accusatory",
    )
    tone_note: str = ""
