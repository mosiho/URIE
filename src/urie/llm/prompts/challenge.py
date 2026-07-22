"""Challenge-loop phrasing prompt — contradictory fact → gentle 'why' question."""

from __future__ import annotations

import json
from typing import Any

from urie.llm.prompts.persona import GUARDRAILS, PERSONA, PROMPT_VERSION

SYSTEM = f"""{PERSONA}

{GUARDRAILS}

A new claim contradicts a stored fact. Freeze the write and ask WHY — capture the
human narrative (buyout, spouse preference, timeline shift), not just the new number.

Tone: curious colleague, never accusatory. One short spoken question.

Output ONLY JSON matching ChallengePhrasing:
{{"vui_prompt":"...","tone_note":"..."}}

prompt_version={PROMPT_VERSION}
"""


def render_challenge_user(
    *,
    subject_spoken: str,
    entity: str,
    existing_value: Any,
    candidate_value: Any,
) -> str:
    return (
        f"Subject: {subject_spoken}\n"
        f"Entity: {entity}\n"
        f"Existing: {json.dumps(existing_value, default=str)}\n"
        f"New claim: {json.dumps(candidate_value, default=str)}\n\n"
        "Phrase the challenge question as JSON."
    )
