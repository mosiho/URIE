"""Constraint-gated ghost-mode reasoning (§6.1–6.2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence


@dataclass(frozen=True)
class ActiveConstraint:
    edge_id: str
    constraint_node_id: str
    label: str  # e.g. Do-Not-Disturb: high workload
    window_start: Optional[datetime]
    window_end: Optional[datetime]

    def is_active_at(self, when: datetime) -> bool:
        if self.window_start and when < self.window_start:
            return False
        if self.window_end and when >= self.window_end:
            return False
        # Open-ended DND without end still blocks
        if self.window_start is None and self.window_end is None:
            return True
        if self.window_start and self.window_end is None:
            return when >= self.window_start
        if self.window_start is None and self.window_end:
            return when < self.window_end
        return True


@dataclass(frozen=True)
class Opportunity:
    subject_node_id: str
    subject_name: str
    trait_summary: str
    mutation_event_id: str


@dataclass(frozen=True)
class GhostModeDecision:
    """Either release a script or hold until constraint clears."""

    held: bool
    held_until: Optional[datetime]
    script: str
    rationale: str
    gifting_suggestion: Optional[str] = None
    blocking_constraint_label: Optional[str] = None


def blocking_constraint(
    constraints: Sequence[ActiveConstraint],
    when: datetime | None = None,
) -> Optional[ActiveConstraint]:
    when = when or datetime.now(timezone.utc)
    for c in constraints:
        if c.is_active_at(when):
            return c
    return None


def decide_ghost_mode(
    opportunity: Opportunity,
    constraints: Sequence[ActiveConstraint],
    when: datetime | None = None,
    synthesized_script: str | None = None,
    synthesized_rationale: str | None = None,
    gifting_suggestion: str | None = None,
) -> GhostModeDecision:
    """
    If an active CONSTRAINED_BY → Do-Not-Disturb edge exists, log the opportunity
    but suppress outward suggestions until the window clears (§6.2).
    """
    when = when or datetime.now(timezone.utc)
    blocker = blocking_constraint(constraints, when)
    if blocker:
        return GhostModeDecision(
            held=True,
            held_until=blocker.window_end,
            script=synthesized_script
            or f"[HELD] Opportunity for {opportunity.subject_name}: {opportunity.trait_summary}",
            rationale=(
                f"Blocked by constraint '{blocker.label}'"
                + (f" until {blocker.window_end.isoformat()}" if blocker.window_end else "")
            ),
            gifting_suggestion=None,
            blocking_constraint_label=blocker.label,
        )

    script = synthesized_script or (
        f"Reach out to {opportunity.subject_name} — mention {opportunity.trait_summary} "
        f"to show you remembered."
    )
    rationale = synthesized_rationale or (
        f"Recent graph mutation: {opportunity.trait_summary} on {opportunity.subject_name}."
    )
    return GhostModeDecision(
        held=False,
        held_until=None,
        script=script,
        rationale=rationale,
        gifting_suggestion=gifting_suggestion,
        blocking_constraint_label=None,
    )
