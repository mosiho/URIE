"""Entity resolution scoring (§5.1 Ambiguity Matrix)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Sequence

from rapidfuzz.distance import JaroWinkler


class ResolutionAction(str, Enum):
    UPSERT = "upsert"  # >= 0.85
    CLARIFY = "clarify"  # 0.45 – 0.85
    CREATE = "create"  # < 0.45


@dataclass(frozen=True)
class ERWeights:
    w1: float = 0.5  # name similarity
    w2: float = 0.3  # graph overlap
    w3: float = 0.2  # recency
    lambda_decay: float = 0.01

    def normalized(self) -> ERWeights:
        total = self.w1 + self.w2 + self.w3
        if total <= 0:
            return ERWeights()
        return ERWeights(
            w1=self.w1 / total,
            w2=self.w2 / total,
            w3=self.w3 / total,
            lambda_decay=self.lambda_decay,
        )


@dataclass
class CandidateNode:
    node_id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    neighbor_ids: set[str] = field(default_factory=set)
    last_touched_at: Optional[datetime] = None


@dataclass(frozen=True)
class MatchResult:
    node_id: Optional[str]
    score: float
    action: ResolutionAction
    hint: str = ""
    candidates: tuple[tuple[str, float, str], ...] = ()  # (node_id, score, hint)


def jaro_winkler_name(spoken: str, candidate: CandidateNode) -> float:
    token = spoken.strip().lower()
    names = [candidate.name] + list(candidate.aliases)
    if not token or not names:
        return 0.0
    best = 0.0
    for n in names:
        # rapidfuzz JaroWinkler.similarity returns 0..1
        best = max(best, JaroWinkler.similarity(token, n.strip().lower()))
    return best


def jaccard_overlap(context_neighbors: set[str], candidate_neighbors: set[str]) -> float:
    if not context_neighbors and not candidate_neighbors:
        return 0.0
    if not context_neighbors or not candidate_neighbors:
        return 0.0
    inter = len(context_neighbors & candidate_neighbors)
    union = len(context_neighbors | candidate_neighbors)
    return inter / union if union else 0.0


def recency_score(last_touched: Optional[datetime], now: Optional[datetime], lambda_decay: float) -> float:
    """exp(-λ · Δt) where Δt is days since last touch."""
    if last_touched is None:
        return 0.0
    now = now or datetime.now(timezone.utc)
    if last_touched.tzinfo is None:
        last_touched = last_touched.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    delta_days = max(0.0, (now - last_touched).total_seconds() / 86400.0)
    return math.exp(-lambda_decay * delta_days)


def match_score(
    spoken: str,
    candidate: CandidateNode,
    context_neighbors: set[str],
    weights: ERWeights | None = None,
    now: datetime | None = None,
) -> float:
    """
    Match Score = w1 · JaroWinkler(name)
                + w2 · Jaccard(local_graph_overlap)
                + w3 · exp(−λ · Δt)
    """
    w = (weights or ERWeights()).normalized()
    s_name = jaro_winkler_name(spoken, candidate)
    s_jacc = jaccard_overlap(context_neighbors, candidate.neighbor_ids)
    s_rec = recency_score(candidate.last_touched_at, now, w.lambda_decay)
    return w.w1 * s_name + w.w2 * s_jacc + w.w3 * s_rec


def resolve_entity(
    spoken: str,
    candidates: Sequence[CandidateNode],
    context_neighbors: set[str] | None = None,
    weights: ERWeights | None = None,
    now: datetime | None = None,
) -> MatchResult:
    """Apply threshold matrix: ≥0.85 upsert, 0.45–0.85 clarify, <0.45 create."""
    ctx = context_neighbors or set()
    if not candidates:
        return MatchResult(node_id=None, score=0.0, action=ResolutionAction.CREATE)

    scored: list[tuple[CandidateNode, float]] = [
        (c, match_score(spoken, c, ctx, weights, now)) for c in candidates
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    best_node, best_score = scored[0]

    def _hint(c: CandidateNode) -> str:
        if c.aliases:
            return c.aliases[0]
        return c.name

    # Near-exact name/alias match: upsert even if graph/recency keep the composite
    # below 0.85 (common on first re-mention of a person with no shared neighbors yet).
    best_jw = jaro_winkler_name(spoken, best_node)
    if best_jw >= 0.98:
        second_jw = jaro_winkler_name(spoken, scored[1][0]) if len(scored) > 1 else 0.0
        if best_jw - second_jw >= 0.05 or len(scored) == 1:
            return MatchResult(
                node_id=best_node.node_id,
                score=max(best_score, 0.85),
                action=ResolutionAction.UPSERT,
                hint=_hint(best_node),
            )

    if best_score >= 0.85:
        return MatchResult(
            node_id=best_node.node_id,
            score=best_score,
            action=ResolutionAction.UPSERT,
            hint=_hint(best_node),
        )

    if best_score >= 0.45:
        top = scored[:3]
        cand_tuples = tuple((c.node_id, s, _hint(c)) for c, s in top)
        return MatchResult(
            node_id=None,
            score=best_score,
            action=ResolutionAction.CLARIFY,
            hint=_hint(best_node),
            candidates=cand_tuples,
        )

    return MatchResult(
        node_id=None,
        score=best_score,
        action=ResolutionAction.CREATE,
        hint="",
    )


def vui_prompt_for_ambiguity(spoken: str, candidates: Sequence[tuple[str, float, str]]) -> str:
    if len(candidates) >= 2:
        a, b = candidates[0], candidates[1]
        return f"{spoken} — {a[2]}, or {b[2]}?"
    if candidates:
        return f"Did you mean {candidates[0][2]}?"
    return f"Who is {spoken}?"
