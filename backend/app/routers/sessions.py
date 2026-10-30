"""Session and taste-profile routes.

Adding a signal resolves the name through Qloo first, so every stored signal
carries a real entity id, type and pillar — the agent can then feed it straight
back into /v2/insights without a second lookup.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent import taste_read
from app.qloo import PILLARS, get_client
from app.qloo.service import QlooError
from app.storage import EntitySignal, Message, Session, SessionNotFound, TagSignal, store
from app.storage.models import Sentiment

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    title: str = "New session"


class AddSignalRequest(BaseModel):
    """Either name something ("Inception") or pass an entity_id you already have."""

    query: str | None = None
    entity_id: str | None = None
    type: str | None = Field(default=None, description="Optional type hint, e.g. 'movie'")
    sentiment: Sentiment = "like"
    source: str = "user"


class AddTagRequest(BaseModel):
    tag_id: str
    name: str | None = None
    sentiment: Sentiment = "like"


class AddMessageRequest(BaseModel):
    role: str
    content: str


def _load(session_id: str) -> Session:
    try:
        return store.get(session_id)
    except SessionNotFound:
        raise HTTPException(status_code=404, detail=f"No session {session_id}") from None


@router.post("", response_model=Session)
def create_session(body: CreateSessionRequest):
    return store.create(body.title)


@router.get("")
def list_sessions():
    return store.list()


@router.get("/{session_id}", response_model=Session)
def get_session(session_id: str):
    return _load(session_id)


@router.delete("/{session_id}")
def delete_session(session_id: str):
    try:
        store.delete(session_id)
    except SessionNotFound:
        raise HTTPException(status_code=404, detail=f"No session {session_id}") from None
    return {"deleted": session_id}


@router.get("/{session_id}/profile")
def get_profile(session_id: str):
    session = _load(session_id)
    coverage = session.profile.pillar_coverage()
    return {
        "profile": session.profile,
        "pillar_coverage": coverage,
        "pillars_missing": [
            key for key, count in coverage.items() if count == 0
        ],
        "pillar_labels": {key: p["label"] for key, p in PILLARS.items()},
    }


@router.get("/{session_id}/taste-read")
async def get_taste_read(session_id: str):
    """The tags that recur across everything they like."""
    return await taste_read.build(_load(session_id))


@router.post("/{session_id}/signals/{entity_id}/dislike", response_model=Session)
def dislike_signal(session_id: str, entity_id: str):
    """Mark a recommendation as wrong for them, so it never comes back."""
    session = _load(session_id)

    existing = next((s for s in session.profile.entities if s.id == entity_id), None)
    if existing:
        existing.sentiment = "dislike"
    else:
        shown = _find_shown(session, entity_id)
        if shown is None:
            raise HTTPException(status_code=404, detail=f"No entity {entity_id} in this session")
        shown.sentiment = "dislike"
        session.profile.entities.append(shown)

    session.remember_shown([entity_id])
    return store.save(session)


def _find_shown(session: Session, entity_id: str) -> EntitySignal | None:
    """Recover an entity the agent recommended earlier in this conversation."""
    for message in reversed(session.messages):
        for rec in message.recommendations:
            if rec.entity.id == entity_id:
                return EntitySignal.from_entity(rec.entity, sentiment="dislike", source="agent")
    return None


@router.post("/{session_id}/signals", response_model=Session)
async def add_signal(session_id: str, body: AddSignalRequest):
    if not body.query and not body.entity_id:
        raise HTTPException(status_code=400, detail="Pass either query or entity_id")

    session = _load(session_id)
    client = get_client()

    try:
        if body.entity_id:
            matches = await client.entities([body.entity_id])
        else:
            matches = await client.search(body.query, entity_type=body.type, take=1)
    except QlooError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"Qloo found nothing for {body.query or body.entity_id!r}",
        )

    signal = EntitySignal.from_entity(
        matches[0],
        sentiment=body.sentiment,
        source="agent" if body.source == "agent" else "user",
    )

    # Re-adding something already in the profile updates it instead of duplicating.
    existing = next((s for s in session.profile.entities if s.id == signal.id), None)
    if existing:
        session.profile.entities.remove(existing)
    session.profile.entities.append(signal)

    if session.title == "New session" and signal.sentiment == "like":
        session.title = signal.name

    return store.save(session)


@router.delete("/{session_id}/signals/{entity_id}", response_model=Session)
def remove_signal(session_id: str, entity_id: str):
    session = _load(session_id)
    remaining = [s for s in session.profile.entities if s.id != entity_id]
    if len(remaining) == len(session.profile.entities):
        raise HTTPException(status_code=404, detail=f"No signal {entity_id}")
    session.profile.entities = remaining
    return store.save(session)


@router.post("/{session_id}/tags", response_model=Session)
def add_tag(session_id: str, body: AddTagRequest):
    session = _load(session_id)
    session.profile.tags = [t for t in session.profile.tags if t.id != body.tag_id]
    session.profile.tags.append(
        TagSignal(id=body.tag_id, name=body.name or body.tag_id, sentiment=body.sentiment)
    )
    return store.save(session)


@router.post("/{session_id}/messages", response_model=Session)
def add_message(session_id: str, body: AddMessageRequest):
    if body.role not in ("user", "agent"):
        raise HTTPException(status_code=400, detail="role must be 'user' or 'agent'")
    session = _load(session_id)
    session.messages.append(Message(role=body.role, content=body.content))
    return store.save(session)
