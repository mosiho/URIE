"""Interview planning prompt — pick the next targeted question from knowledge gaps."""

from __future__ import annotations

import json
from typing import Any

from urie.llm.prompts.persona import GUARDRAILS, PERSONA, PROMPT_VERSION

SYSTEM = f"""{PERSONA}

{GUARDRAILS}

You are mid-debrief with the agent. Your job: choose ONE next question that closes the
highest-priority knowledge gap — or end the interview if gaps are exhausted or the
agent is clearly done.

Question craft:
- Short, spoken, warm, never interrogative-police.
- Ask about what you DON'T yet understand (gaps), not what you already know.
- Prefer narrative ("what shifted?") over yes/no.
- One question only. No multi-part laundry lists.
- If the graph is empty, open with a natural "What happened today with your clients?"

Output ONLY JSON matching InterviewPlan:
{{"next_question":"...","target_gap":"...or null","done":false,"reason":"..."}}

Set done=true when: no meaningful gaps remain, max turns reached (caller will also
enforce), or the agent signalled they're finished.

prompt_version={PROMPT_VERSION}
"""


def render_interview_user(
    *,
    gaps: list[dict[str, Any]],
    recent_turns: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
    max_turns: int = 8,
    turn_index: int = 0,
) -> str:
    return (
        f"Turn index: {turn_index} / max {max_turns}\n"
        f"Open knowledge gaps (priority desc):\n{json.dumps(gaps, default=str, indent=2)[:3000]}\n\n"
        f"Recent turns:\n{json.dumps(recent_turns[-6:], default=str, indent=2)[:2000]}\n\n"
        f"Extra context:\n{json.dumps(context or {}, default=str)[:1000]}\n\n"
        "Plan the next interview move as JSON."
    )
