"""Ghost-mode script synthesis prompt."""

from __future__ import annotations

import json
from typing import Any

from urie.llm.prompts.persona import GUARDRAILS, PERSONA, PROMPT_VERSION

SYSTEM = f"""{PERSONA}

{GUARDRAILS}

Produce a hyper-personalized GHOST-MODE script the agent will execute themselves.
The client should feel remembered — never pinged by a robot.

Craft:
- Open with a specific personal reference (life event, preference, boundary ending).
- Include when/how to reach out if timing matters.
- Rationale: one crisp sentence of why this moment.
- Optional gifting_suggestion: only when a life event warrants it; agent buys/sends it,
  not the system. Never invent medical or financial details the graph doesn't have.

Output ONLY JSON matching GhostScript.

prompt_version={PROMPT_VERSION}
"""


def render_ghost_user(
    subject_name: str,
    trait_summary: str,
    context: dict[str, Any] | None = None,
) -> str:
    return (
        f"Subject: {subject_name}\n"
        f"Trigger / trait: {trait_summary}\n"
        f"Sub-graph context:\n{json.dumps(context or {}, default=str, indent=2)[:2500]}\n\n"
        "Write the ghost-mode script as JSON."
    )
