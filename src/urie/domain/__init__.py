"""Domain package — pure, I/O-free engine logic."""

from urie.domain.challenge import CandidateMutation, Challenge, detect_contradiction
from urie.domain.entity_resolution import (
    ERWeights,
    MatchResult,
    ResolutionAction,
    resolve_entity,
)
from urie.domain.facts import (
    CONFLICT_RESOLUTION_CONFIDENCE,
    ConditionalField,
    Fact,
    Money,
    conflict_resolution_fact,
    supersede,
)
from urie.domain.reasoning import (
    ActiveConstraint,
    GhostModeDecision,
    Opportunity,
    decide_ghost_mode,
)

__all__ = [
    "ActiveConstraint",
    "CONFLICT_RESOLUTION_CONFIDENCE",
    "CandidateMutation",
    "Challenge",
    "ConditionalField",
    "ERWeights",
    "Fact",
    "GhostModeDecision",
    "MatchResult",
    "Money",
    "Opportunity",
    "ResolutionAction",
    "conflict_resolution_fact",
    "decide_ghost_mode",
    "detect_contradiction",
    "resolve_entity",
    "supersede",
]
