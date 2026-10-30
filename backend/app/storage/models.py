"""What a session holds on disk.

A session is the whole memory of one person's conversation: the taste signals
they have given, what the agent recommended, and the chat itself. It is stored
as a single JSON file so it can be inspected, copied or hand-edited.
"""

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.qloo.entity_types import PILLARS
from app.qloo.models import Entity

SignalSource = Literal["user", "agent"]
Sentiment = Literal["like", "dislike"]


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class EntitySignal(BaseModel):
    """One taste anchor: something the person likes (or explicitly does not)."""

    id: str
    name: str
    type: str | None = None
    type_label: str | None = None
    pillar: str | None = None
    image: str | None = None
    sentiment: Sentiment = "like"
    source: SignalSource = "user"
    added_at: datetime = Field(default_factory=now)

    @classmethod
    def from_entity(
        cls,
        entity: Entity,
        sentiment: Sentiment = "like",
        source: SignalSource = "user",
    ) -> "EntitySignal":
        return cls(
            id=entity.id,
            name=entity.name,
            type=entity.type,
            type_label=entity.type_label,
            pillar=entity.pillar,
            image=entity.image,
            sentiment=sentiment,
            source=source,
        )


class TagSignal(BaseModel):
    id: str
    name: str
    sentiment: Sentiment = "like"
    source: SignalSource = "user"
    added_at: datetime = Field(default_factory=now)


class TasteProfile(BaseModel):
    """Everything the agent knows about this person's taste so far."""

    entities: list[EntitySignal] = Field(default_factory=list)
    tags: list[TagSignal] = Field(default_factory=list)
    #: Where they are, or where they are headed - used to ground place results.
    location: str | None = None

    def liked_entity_ids(self) -> list[str]:
        return [e.id for e in self.entities if e.sentiment == "like"]

    def disliked_entity_ids(self) -> list[str]:
        return [e.id for e in self.entities if e.sentiment == "dislike"]

    def liked_tag_ids(self) -> list[str]:
        return [t.id for t in self.tags if t.sentiment == "like"]

    def pillar_coverage(self) -> dict[str, int]:
        """How many liked signals sit in each pillar — drives the 'all four
        pillars' requirement and tells the agent where it is still blind."""
        counts = {key: 0 for key in PILLARS}
        for signal in self.entities:
            if signal.sentiment == "like" and signal.pillar in counts:
                counts[signal.pillar] += 1
        return counts

    def is_empty(self) -> bool:
        return not self.entities and not self.tags


class Recommendation(BaseModel):
    """An entity the agent surfaced, kept so it is never repeated."""

    entity: Entity
    reason: str | None = None
    shown_at: datetime = Field(default_factory=now)


class Message(BaseModel):
    id: str = Field(default_factory=lambda: new_id("msg"))
    role: Literal["user", "agent"]
    content: str
    recommendations: list[Recommendation] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now)


class Session(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ses"))
    title: str = "New session"
    profile: TasteProfile = Field(default_factory=TasteProfile)
    messages: list[Message] = Field(default_factory=list)
    shown_entity_ids: list[str] = Field(default_factory=list)
    #: Pillar the agent asked about last, so it does not ask twice in a row.
    last_asked_pillar: str | None = None
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

    def touch(self) -> None:
        self.updated_at = now()

    def remember_shown(self, entity_ids: list[str]) -> None:
        for entity_id in entity_ids:
            if entity_id not in self.shown_entity_ids:
                self.shown_entity_ids.append(entity_id)

    def summary(self) -> "SessionSummary":
        return SessionSummary(
            id=self.id,
            title=self.title,
            signal_count=len(self.profile.entities),
            message_count=len(self.messages),
            pillar_coverage=self.profile.pillar_coverage(),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class SessionSummary(BaseModel):
    id: str
    title: str
    signal_count: int
    message_count: int
    pillar_coverage: dict[str, int]
    created_at: datetime
    updated_at: datetime
