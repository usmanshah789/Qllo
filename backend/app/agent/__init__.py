"""Picks a brain and keeps the session in step with the conversation.

Whichever LLM key is in .env decides who answers: Claude, Groq, or - with
neither - the rule-based planner. If the model call fails mid-demo the planner
takes over rather than showing an error.
"""

import logging

from app import config
from app.agent import planner
from app.agent.base import GREETING, AgentReply, ToolCall
from app.storage.models import Message, Recommendation, Session

log = logging.getLogger(__name__)

__all__ = ["respond", "current_brain", "AgentReply", "ToolCall", "GREETING"]


def current_brain() -> str:
    return config.LLM_PROVIDER if config.USE_LLM else "rules"


async def respond(session: Session, text: str) -> AgentReply:
    """Answer one message and record both sides on the session.

    The caller is responsible for saving; this keeps the whole exchange in one
    object so nothing is written twice.
    """
    session.messages.append(Message(role="user", content=text))

    # Parsing the message is cheap and provider-independent, so do it for every
    # brain. It also means an LLM brain starts with the entity ids already in
    # its prompt instead of spending tool calls looking them up again.
    city = planner.detect_location(text)
    if city:
        session.profile.location = city

    parsed = await planner.resolve_mentions(session, text)

    reply: AgentReply
    if config.USE_LLM:
        try:
            if config.LLM_PROVIDER == "anthropic":
                from app.agent import brain as llm
            else:
                from app.agent import groq_brain as llm

            reply = await llm.respond(session, text)
        except Exception as exc:  # noqa: BLE001 - never lose the turn to a model error
            log.warning("%s brain failed, falling back to planner: %s",
                        config.LLM_PROVIDER, exc)
            reply = await planner.respond(session, text)
    else:
        reply = await planner.respond(session, text)

    known = {s.id for s in reply.new_signals}
    reply.new_signals = reply.new_signals + [s for s in parsed if s.id not in known]

    session.messages.append(
        Message(
            role="agent",
            content=reply.message,
            recommendations=[
                Recommendation(entity=entity) for entity in reply.recommendations
            ],
        )
    )

    if session.title == "New session":
        liked = [s for s in session.profile.entities if s.sentiment == "like"]
        if liked:
            session.title = liked[0].name

    return reply
