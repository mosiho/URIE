"""Extraction prompt — agent speech → structured mutations."""

from __future__ import annotations

import json
from typing import Any

from urie.llm.prompts.persona import GUARDRAILS, PERSONA, PROMPT_VERSION, SPEECH_HINTS

SYSTEM = f"""{PERSONA}

{GUARDRAILS}

{SPEECH_HINTS}

Your job this turn: EXTRACT structured relationship facts from the agent's spoken/written
debrief turn. Emit ONLY valid JSON matching the ExtractionResult schema.

Entity types you commonly emit:
- Budget — purchasing power / offer ceiling (money object)
- LifeEvent — baby, divorce, job change, relocation driver, etc. (use edge_type=HAS_TRAIT)
- Constraint — Do-Not-Disturb / high workload / travel window (edge_type=CONSTRAINED_BY;
  value should include label + optional window_end as YYYY-MM-DD)
- Preference / Timeline / DecisionMaker / Note — as appropriate
- RELATES_TO / DECIDES_FOR edges when the agent names spouse, lawyer, referrer, etc.

Few-shot:
Input: "Met John — budget's around three million, maybe five if the bonus comes."
Output mutations: [{{"entity":"Budget","subject_spoken":"John","value":{{"amount":3000000,"currency":"USD"}},"is_hypothesis":true,"confidence":0.7}}]

Input: "John's wife is expecting a baby."
Output: [{{"entity":"LifeEvent","subject_spoken":"John","value":"expecting_a_baby","edge_type":"HAS_TRAIT","trait_name":"Expecting a baby","is_hypothesis":false,"confidence":0.9}}]

Input: "Don't contact John until 2026-07-28 — crazy week at work."
Output: [{{"entity":"Constraint","subject_spoken":"John","value":{{"label":"Do-Not-Disturb: high workload","window_end":"2026-07-28"}},"edge_type":"CONSTRAINED_BY","trait_name":"Do-Not-Disturb: high workload","confidence":0.95}}]

If nothing extractable, return {{"mutations":[],"summary":"..."}}.

prompt_version={PROMPT_VERSION}
"""


def render_extraction_user(
    turn_text: str,
    *,
    known_people: list[str] | None = None,
    recent_context: dict[str, Any] | None = None,
) -> str:
    people = ", ".join(known_people or []) or "(none yet)"
    ctx = json.dumps(recent_context or {}, default=str)[:1500]
    return (
        f"Known people in this agent's book: {people}\n"
        f"Session context (json): {ctx}\n\n"
        f"Agent turn:\n\"\"\"\n{turn_text.strip()}\n\"\"\"\n\n"
        "Extract mutations now as JSON."
    )
