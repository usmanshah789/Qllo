"""Turning a tool lookup into a stored taste signal.

The planner records signals as it parses the message. An LLM brain never parses
anything, so without this the profile would stay empty no matter how long the
conversation ran - and pillar coverage, deduping and the saved profile would all
be dead weight.
"""

from app.agent.planner import plausible_match
from app.qloo.models import Entity
from app.storage.models import EntitySignal, Session


def record_lookup(
    session: Session,
    query: str,
    entity: Entity,
    said_by_user: str | None = None,
) -> EntitySignal | None:
    """Store what the model just looked up, if it is really a stated taste.

    The model also searches while hunting for recommendations ("futuristic
    restaurant Tokyo"), and those hits are not preferences. Only keep a lookup
    the person's own words asked for.
    """
    if not entity.id or not plausible_match(query, entity.name):
        return None
    if said_by_user is not None and not _user_said(session, said_by_user, query, entity.name):
        return None
    if any(s.id == entity.id for s in session.profile.entities):
        return None

    signal = EntitySignal.from_entity(entity, source="agent")
    session.profile.entities.append(signal)
    return signal


def _user_said(session: Session, text: str, query: str, name: str) -> bool:
    """The model often looks up something named several turns ago, so check the
    recent conversation, not only the message that triggered this turn."""
    spoken = [text] + [m.content for m in session.messages[-8:] if m.role == "user"]
    haystack = " ".join(spoken).lower()
    return query.lower() in haystack or name.lower() in haystack
