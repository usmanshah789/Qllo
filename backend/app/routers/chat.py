"""The one endpoint the UI talks to."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import agent
from app.agent.base import GREETING, AgentReply
from app.storage import Session, SessionNotFound, store

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: AgentReply
    session: Session


@router.get("/greeting")
def greeting():
    return {"message": GREETING, "brain": agent.current_brain()}


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    if body.session_id:
        try:
            session = store.get(body.session_id)
        except SessionNotFound:
            raise HTTPException(status_code=404, detail=f"No session {body.session_id}") from None
    else:
        session = store.create()

    reply = await agent.respond(session, body.message)
    store.save(session)

    return ChatResponse(session_id=session.id, reply=reply, session=session)
