"""Thin HTTP surface over the Qloo layer.

These routes exist so the Qloo layer can be exercised on its own; the agent
endpoints added later call the same client directly.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.qloo import ENTITY_TYPES, PILLARS, Entity, Tag, get_client
from app.qloo.service import QlooError, current_mode

router = APIRouter(prefix="/api/qloo", tags=["qloo"])


class InsightsRequest(BaseModel):
    target_type: str = Field(..., examples=["urn:entity:place"])
    signal_entities: list[str] = Field(default_factory=list)
    signal_tags: list[str] = Field(default_factory=list)
    take: int = 10


class CompareRequest(BaseModel):
    group_a: list[str]
    group_b: list[str]
    target_type: str
    take: int = 10


def _guard(exc: QlooError) -> HTTPException:
    return HTTPException(status_code=502, detail=str(exc))


@router.get("/types")
def list_types():
    return {
        "mode": current_mode(),
        "entity_types": ENTITY_TYPES,
        "pillars": {
            key: {"label": p["label"], "types": p["types"]}
            for key, p in PILLARS.items()
        },
    }


@router.get("/search", response_model=list[Entity])
async def search(
    q: str = Query(..., min_length=1),
    type: str | None = None,
    take: int = 10,
):
    try:
        return await get_client().search(q, entity_type=type, take=take)
    except QlooError as exc:
        raise _guard(exc) from exc


@router.get("/tags", response_model=list[Tag])
async def tags(q: str = Query("", description="Blank returns popular tags"), take: int = 10):
    try:
        return await get_client().tags(q, take=take)
    except QlooError as exc:
        raise _guard(exc) from exc


@router.post("/insights", response_model=list[Entity])
async def insights(body: InsightsRequest):
    try:
        return await get_client().insights(
            body.target_type,
            signal_entities=body.signal_entities,
            signal_tags=body.signal_tags,
            take=body.take,
        )
    except QlooError as exc:
        raise _guard(exc) from exc


@router.post("/compare", response_model=list[Tag])
async def compare(body: CompareRequest):
    try:
        return await get_client().compare(
            body.group_a, body.group_b, body.target_type, take=body.take
        )
    except QlooError as exc:
        raise _guard(exc) from exc
