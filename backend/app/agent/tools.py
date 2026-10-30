"""The Qloo actions the agent is allowed to take.

Each tool has a JSON schema (for Claude's tool-use API) and a plain async
implementation. The rule-based planner calls the implementations directly, so
both brains work off exactly the same capabilities.
"""

from typing import Any

from app.qloo import PILLARS, get_client
from app.qloo.entity_types import (
    ENTITY_TYPES,
    RECOMMENDABLE,
    SEARCHABLE,
    normalize_type,
    types_for_pillar,
)
from app.qloo.models import Entity
from app.qloo.service import QlooError

def _aliases(urns) -> list[str]:
    return sorted(urn.rsplit(":", 1)[-1] for urn in urns)


TYPE_ALIASES = _aliases(ENTITY_TYPES)
SEARCH_ALIASES = _aliases(SEARCHABLE)
TARGET_ALIASES = _aliases(RECOMMENDABLE)

#: Narrowing tags for places, so "coffee in Berlin" does not return landmarks.
PLACE_CATEGORIES = {
    "restaurant": "urn:tag:genre:place:restaurant",
    "cafe": "urn:tag:genre:place:restaurant:cafe",
    "bar": "urn:tag:genre:place:restaurant:bar",
    "hotel": "urn:tag:genre:place:hotel",
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_entity",
        "description": "Find something by name in Qloo and get its entity id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "type": {"type": "string", "enum": SEARCH_ALIASES},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_recommendations",
        "description": (
            "Cross-domain recommendations: given taste signals, what would they "
            "also like in another domain. Pass location for places."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target_type": {"type": "string", "enum": TARGET_ALIASES},
                "entity_ids": {"type": "array", "items": {"type": "string"}},
                "tag_ids": {"type": "array", "items": {"type": "string"}},
                "location": {"type": "string", "description": "City, required for places"},
                "category": {
                    "type": "string",
                    "enum": sorted(PLACE_CATEGORIES),
                    "description": "Narrows places to a kind of venue",
                },
                "take": {"type": "integer"},
            },
            "required": ["target_type"],
        },
    },
    {
        "name": "find_tags",
        "description": "Get Qloo tag ids for a mood, genre or style word.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "compare_tastes",
        "description": "Tags that distinguish two groups of tastes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "group_a": {"type": "array", "items": {"type": "string"}},
                "group_b": {"type": "array", "items": {"type": "string"}},
                "target_type": {"type": "string", "enum": TARGET_ALIASES},
            },
            "required": ["group_a", "group_b", "target_type"],
        },
    },
]


def _entity_brief(entity: Entity) -> dict:
    """Trimmed shape for the model: enough to reason with, no payload bloat."""
    return {
        "id": entity.id,
        "name": entity.name,
        "type": entity.type_label,
        "pillar": entity.pillar,
        "year": entity.subtitle,
        "why": (entity.description or "")[:90] or None,
        "address": entity.address,
        "affinity": entity.affinity,
        "tags": [t.name for t in entity.tags[:4]],
    }


async def search_entity(
    query: str,
    type: str | None = None,
    take: int = 3,
    _sink: dict[str, Entity] | None = None,
) -> dict:
    results = await get_client().search(query, entity_type=type, take=take)
    if _sink is not None:
        _sink.update({e.id: e for e in results if e.id})
    return {"results": [_entity_brief(e) for e in results]}


async def get_recommendations(
    target_type: str,
    entity_ids: list[str] | None = None,
    tag_ids: list[str] | None = None,
    take: int = 5,
    location: str | None = None,
    category: str | None = None,
    filter_tags: list[str] | None = None,
    exclude_ids: list[str] | None = None,
    _sink: dict[str, Entity] | None = None,
) -> dict:
    if not entity_ids and not tag_ids:
        return {"error": "Need at least one entity_id or tag_id as a signal."}

    narrowing = list(filter_tags or [])
    if category and category in PLACE_CATEGORIES:
        narrowing.append(PLACE_CATEGORIES[category])

    blocked = set(exclude_ids or [])
    # Over-fetch so filtering duplicates and already-shown items still leaves enough.
    raw = await get_client().insights(
        target_type,
        signal_entities=entity_ids or [],
        signal_tags=tag_ids or [],
        location=location,
        filter_tags=narrowing,
        take=max(take * 3, 15),
    )

    seen: set[str] = set()
    results = []
    for entity in raw:
        if entity.id in blocked or entity.id in seen:
            continue
        seen.add(entity.id)
        results.append(entity)
        if len(results) >= take:
            break

    if _sink is not None:
        _sink.update({e.id: e for e in results if e.id})
    return {"results": [_entity_brief(e) for e in results]}


async def find_tags(query: str, take: int = 5) -> dict:
    tags = await get_client().tags(query, take=take)
    return {"results": [{"id": t.id, "name": t.name, "type": t.type} for t in tags]}


async def compare_tastes(
    group_a: list[str],
    group_b: list[str],
    target_type: str,
    take: int = 8,
) -> dict:
    tags = await get_client().compare(group_a, group_b, target_type, take=take)
    return {"results": [{"name": t.name, "type": t.type, "score": t.score} for t in tags]}


IMPLEMENTATIONS = {
    "search_entity": search_entity,
    "get_recommendations": get_recommendations,
    "find_tags": find_tags,
    "compare_tastes": compare_tastes,
}


#: Tools that can hand back full Entity objects for the reply cards.
ENTITY_TOOLS = {"search_entity", "get_recommendations"}


async def run_tool(
    name: str,
    arguments: dict,
    sinks: dict[str, dict[str, Entity]] | None = None,
    exclude_ids: list[str] | None = None,
) -> dict:
    impl = IMPLEMENTATIONS.get(name)
    if impl is None:
        return {"error": f"Unknown tool {name}"}

    arguments = dict(arguments)
    if name in ENTITY_TOOLS and sinks is not None:
        arguments["_sink"] = sinks.setdefault(name, {})
    if name == "get_recommendations" and exclude_ids:
        arguments.setdefault("exclude_ids", exclude_ids)

    try:
        return await impl(**arguments)
    except QlooError as exc:
        return {"error": f"Qloo unavailable: {exc}"}
    except TypeError as exc:
        return {"error": f"Bad arguments for {name}: {exc}"}


def pillar_hint() -> str:
    """Reference block for the system prompt."""
    lines = []
    for key, pillar in PILLARS.items():
        aliases = ", ".join(t.rsplit(":", 1)[-1] for t in types_for_pillar(key))
        lines.append(f"- {key} ({pillar['label']}): {aliases}")
    return "\n".join(lines)


def resolve_type(value: str | None) -> str | None:
    return normalize_type(value)
