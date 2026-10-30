"""Shared result shape for both brains."""

from typing import Literal

from pydantic import BaseModel, Field

from app.qloo.models import Entity
from app.storage.models import EntitySignal

GREETING = (
    "Tell me something you love — a film, a show, an album, a brand, anywhere "
    "you have been happy — and I will find the rest of your taste."
)


class ToolCall(BaseModel):
    name: str
    arguments: dict
    result_summary: str


class AgentReply(BaseModel):
    message: str
    recommendations: list[Entity] = Field(default_factory=list)
    new_signals: list[EntitySignal] = Field(default_factory=list)
    brain: Literal["rules", "claude", "groq"] = "rules"
    asked_about: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
