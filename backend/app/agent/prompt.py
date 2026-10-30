"""Prompt and context shared by every LLM brain.

Both providers get the same instructions and the same view of the profile, so
swapping one for the other changes the wording, never the behaviour.
"""

from app.agent import tools
from app.qloo.models import Entity
from app.storage.models import Session

SYSTEM_PROMPT = """You are a taste agent. You learn what someone likes, then show them things they would not have found alone, across domains: a film can lead to a bar, a brand, a city, a writer.

Qloo is your only source of taste data. Never invent a recommendation or a rating. If you have not looked it up with a tool, you do not know it.

Rules:
- search_entity is ONLY for pinning down something the person named. Never use it to find recommendations - a name search is not a taste match.
- Every recommendation must come from get_recommendations. It needs at least one entity id, from the profile or a fresh search.
- Places need a location, or Qloo returns landmarks from where the film was shot. Ask for the city if you do not know it, and pass category (cafe, bar, restaurant, hotel) so you get venues rather than monuments.
- Two or three picks, each with a reason taken from the tags Qloo returned.
- One question at a time, and only about a domain you know nothing about.

Pillars and their Qloo types:
{pillars}

Tone: a well-read friend who knows the city. Warm, specific, short paragraphs. No sales copy, no "I'd be happy to". Bold a name when you recommend it.

Profile so far:
{profile}
"""


def profile_block(session: Session) -> str:
    profile = session.profile
    if profile.is_empty():
        return "Nothing yet - this is the first thing they have told you."

    lines = []
    likes = [s for s in profile.entities if s.sentiment == "like"]
    if likes:
        lines.append("Likes:")
        for signal in likes:
            lines.append(f"  - {signal.name} ({signal.type_label}, {signal.pillar}) id={signal.id}")

    dislikes = [s for s in profile.entities if s.sentiment == "dislike"]
    if dislikes:
        lines.append("Does not like: " + ", ".join(s.name for s in dislikes))

    if profile.tags:
        lines.append("Tag signals: " + ", ".join(f"{t.name} ({t.id})" for t in profile.tags))

    if profile.location:
        lines.append(f"Location: {profile.location}")

    coverage = profile.pillar_coverage()
    unexplored = [key for key, count in coverage.items() if count == 0]
    lines.append(f"Pillar coverage: {coverage}")
    if unexplored:
        lines.append(f"Knows nothing about: {', '.join(unexplored)}")

    if session.shown_entity_ids:
        lines.append(
            f"Already recommended {len(session.shown_entity_ids)} things - do not repeat them."
        )

    return "\n".join(lines)


def system_prompt(session: Session) -> str:
    return SYSTEM_PROMPT.format(
        pillars=tools.pillar_hint(),
        profile=profile_block(session),
    )


def history(session: Session, limit: int = 6) -> list[dict]:
    return [
        {
            "role": "user" if message.role == "user" else "assistant",
            "content": message.content[:500],
        }
        for message in session.messages[-limit:]
    ]


_SUFFIXES = (" inc", " inc.", " ltd", " ltd.", " llc", " corp", " corporation", " co.")


def mentioned(text: str, entity: Entity) -> bool:
    """Only show a card for something the model actually named.

    Qloo spells brands formally ("Apple Inc") while the model writes "Apple",
    so compare without the corporate suffix too.
    """
    haystack = text.lower()
    name = entity.name.lower()
    if name in haystack:
        return True
    for suffix in _SUFFIXES:
        if name.endswith(suffix):
            trimmed = name[: -len(suffix)].strip()
            return len(trimmed) > 3 and trimmed in haystack
    return False
