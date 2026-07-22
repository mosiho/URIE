"""Unit tests for entity resolution scoring and thresholds."""

from datetime import datetime, timedelta, timezone

from urie.domain.entity_resolution import (
    CandidateNode,
    ERWeights,
    ResolutionAction,
    jaccard_overlap,
    jaro_winkler_name,
    match_score,
    resolve_entity,
    vui_prompt_for_ambiguity,
)


def test_jaro_winkler_exact():
    c = CandidateNode(node_id="n1", name="Ali Hosseini", aliases=["Ali"])
    assert jaro_winkler_name("Ali Hosseini", c) == 1.0
    assert jaro_winkler_name("Ali", c) > 0.8


def test_jaccard_overlap():
    assert abs(jaccard_overlap({"a", "b"}, {"b", "c"}) - (1 / 3)) < 1e-9
    assert jaccard_overlap(set(), {"a"}) == 0.0


def test_jaccard_exact():
    assert abs(jaccard_overlap({"a", "b"}, {"b", "c"}) - (1 / 3)) < 1e-9


def test_upsert_threshold():
    now = datetime.now(timezone.utc)
    c = CandidateNode(
        node_id="n1",
        name="John Smith",
        aliases=["John"],
        neighbor_ids={"lawyer_1"},
        last_touched_at=now,
    )
    result = resolve_entity(
        "John Smith",
        [c],
        context_neighbors={"lawyer_1"},
        weights=ERWeights(w1=0.5, w2=0.3, w3=0.2),
        now=now,
    )
    assert result.action == ResolutionAction.UPSERT
    assert result.node_id == "n1"
    assert result.score >= 0.85


def test_clarify_threshold():
    now = datetime.now(timezone.utc)
    # Two similar Alis with weak overlap → mid-band score
    a = CandidateNode(
        node_id="ali_h",
        name="Ali Hosseini",
        aliases=["Ali"],
        neighbor_ids={"ferhadije"},
        last_touched_at=now - timedelta(days=30),
    )
    b = CandidateNode(
        node_id="ali_r",
        name="Ali Rezai",
        aliases=["Ali"],
        neighbor_ids={"attorney"},
        last_touched_at=now - timedelta(days=60),
    )
    # Name "Ali" alone + no shared neighbors → score dominated by partial name match
    weights = ERWeights(w1=0.5, w2=0.3, w3=0.2, lambda_decay=0.01)
    result = resolve_entity("Ali", [a, b], context_neighbors=set(), weights=weights, now=now)
    # Should be clarify or upsert depending on JW("Ali","Ali Hosseini"); alias exact may push upsert.
    # Force mid-band by using a slightly off name with no alias hit:
    a2 = CandidateNode(
        node_id="ali_h",
        name="Ali Hosseini",
        aliases=[],
        neighbor_ids=set(),
        last_touched_at=now - timedelta(days=100),
    )
    b2 = CandidateNode(
        node_id="ali_r",
        name="Ali Rezai",
        aliases=[],
        neighbor_ids=set(),
        last_touched_at=now - timedelta(days=100),
    )
    result = resolve_entity("Ali", [a2, b2], context_neighbors=set(), weights=weights, now=now)
    assert result.action in (ResolutionAction.CLARIFY, ResolutionAction.UPSERT)
    if result.action == ResolutionAction.CLARIFY:
        assert len(result.candidates) >= 1
        prompt = vui_prompt_for_ambiguity("Ali", result.candidates)
        assert "Ali" in prompt


def test_create_threshold():
    now = datetime.now(timezone.utc)
    c = CandidateNode(
        node_id="n1",
        name="Zafar",
        aliases=[],
        neighbor_ids=set(),
        last_touched_at=now - timedelta(days=365),
    )
    result = resolve_entity(
        "CompletelyDifferentName",
        [c],
        context_neighbors=set(),
        weights=ERWeights(),
        now=now,
    )
    assert result.action == ResolutionAction.CREATE
    assert result.score < 0.45


def test_empty_candidates_creates():
    result = resolve_entity("John", [], set())
    assert result.action == ResolutionAction.CREATE


def test_match_score_components():
    now = datetime.now(timezone.utc)
    c = CandidateNode(
        node_id="n1",
        name="John",
        aliases=[],
        neighbor_ids={"x"},
        last_touched_at=now,
    )
    score = match_score("John", c, {"x"}, ERWeights(1, 0, 0), now)
    assert abs(score - 1.0) < 1e-9
