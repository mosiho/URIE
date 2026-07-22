"""LLM message types."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    role: Role
    content: str

    @classmethod
    def system(cls, content: str) -> Message:
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> Message:
        return cls(role=Role.USER, content=content)

    @classmethod
    def assistant(cls, content: str) -> Message:
        return cls(role=Role.ASSISTANT, content=content)

    def to_openai(self) -> dict:
        return {"role": self.role.value, "content": self.content}

    def to_anthropic(self) -> Optional[dict]:
        # Anthropic system is separate; skip system here
        if self.role == Role.SYSTEM:
            return None
        return {"role": self.role.value, "content": self.content}
