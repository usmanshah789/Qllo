"""Groq-backed brain.

Groq speaks the OpenAI chat-completions dialect, so the tool loop differs from
Claude's only in message shape. The prompt, the tools and the rule that Qloo is
the only source of taste data are shared with every other brain.

Groq's free tier allows 8000 tokens per minute, which a chatty tool loop will
blow through, so everything here is kept deliberately small: short schemas,
truncated tool results, a short history window, and a single backoff retry when
the limit is hit anyway.
"""

import asyncio
import json
import time

import httpx

from app import config
from app.agent import prompt, signals, tools
from app.agent.base import AgentReply, ToolCall
from app.qloo.models import Entity
from app.storage.models import EntitySignal, Session

MAX_TURNS = 7
MAX_TOKENS = 600
RESULT_CHARS = 1400
TIMEOUT = 60.0


class GroqError(RuntimeError):
    pass


class _Budget:
    """Keeps the session inside Groq's per-minute token allowance.

    Every response reports how much budget is left and when it refills. Reading
    that is cheaper than hitting the limit and retrying, so calls wait when the
    remaining budget would not cover the next one. One call at a time, because
    two chats firing together is what actually overruns the window.
    """

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.remaining: int | None = None
        self.refill_at = 0.0

    async def wait_for_room(self, need: int = 2500) -> None:
        if self.remaining is None or self.remaining >= need:
            return
        delay = self.refill_at - time.monotonic()
        if delay > 0:
            await asyncio.sleep(min(delay + 0.5, 30.0))
        self.remaining = None

    def note(self, headers) -> None:
        try:
            self.remaining = int(float(headers.get("x-ratelimit-remaining-tokens", "")))
        except (TypeError, ValueError):
            self.remaining = None
            return
        raw = headers.get("x-ratelimit-reset-tokens", "") or ""
        try:
            self.refill_at = time.monotonic() + float(raw.rstrip("s"))
        except ValueError:
            self.refill_at = time.monotonic() + 60.0


BUDGET = _Budget()


def _openai_tools() -> list[dict]:
    """Same tools, wrapped in the OpenAI function-calling envelope."""
    return [
        {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["input_schema"],
            },
        }
        for schema in tools.TOOL_SCHEMAS
    ]


def _retry_after(response: httpx.Response) -> float:
    for header in ("retry-after", "x-ratelimit-reset-tokens"):
        value = response.headers.get(header, "").rstrip("s")
        try:
            return min(float(value), 20.0)
        except (TypeError, ValueError):
            continue
    return 5.0


async def _complete(http: httpx.AsyncClient, messages: list[dict]) -> dict:
    payload = {
        "model": config.GROQ_MODEL,
        "messages": messages,
        "tools": _openai_tools(),
        "max_tokens": MAX_TOKENS,
        "temperature": 0.7,
    }
    url = f"{config.GROQ_BASE_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}

    async with BUDGET.lock:
        for attempt in range(3):
            await BUDGET.wait_for_room()
            response = await http.post(url, headers=headers, json=payload)
            BUDGET.note(response.headers)

            if response.status_code == 429 and attempt < 2:
                await asyncio.sleep(_retry_after(response))
                continue
            if response.status_code >= 400:
                raise GroqError(f"Groq returned {response.status_code}: {response.text[:200]}")
            return response.json()["choices"][0]["message"]

    raise GroqError("Groq rate limit did not clear")


async def respond(session: Session, text: str) -> AgentReply:
    messages: list[dict] = (
        [{"role": "system", "content": prompt.system_prompt(session)}]
        + prompt.history(session)
        + [{"role": "user", "content": text}]
    )

    sinks: dict[str, dict[str, Entity]] = {}
    tool_calls: list[ToolCall] = []
    new_signals: list[EntitySignal] = []
    final_text = ""

    async with httpx.AsyncClient(timeout=TIMEOUT) as http:
        for _ in range(MAX_TURNS):
            message = await _complete(http, messages)

            if message.get("content"):
                final_text = message["content"].strip()

            requested = message.get("tool_calls") or []
            if not requested:
                break

            messages.append(message)

            for call in requested:
                name = call["function"]["name"]
                try:
                    arguments = json.loads(call["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    arguments = {}

                known_before = set(sinks.get(name, {}))
                payload = await tools.run_tool(
                    name,
                    arguments,
                    sinks=sinks,
                    exclude_ids=session.shown_entity_ids
                    + session.profile.disliked_entity_ids(),
                )

                # A lookup the model made is a taste signal worth keeping.
                if name == "search_entity":
                    fresh = [
                        entity
                        for key, entity in sinks.get(name, {}).items()
                        if key not in known_before
                    ]
                    for entity in fresh[:1]:
                        signal = signals.record_lookup(
                            session, arguments.get("query", ""), entity, said_by_user=text
                        )
                        if signal:
                            new_signals.append(signal)

                count = len(payload.get("results", [])) if isinstance(payload, dict) else 0
                tool_calls.append(
                    ToolCall(
                        name=name,
                        arguments=arguments,
                        result_summary=payload.get("error") or f"{count} results",
                    )
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(payload)[:RESULT_CHARS],
                    }
                )

        if not final_text:
            # The loop ran out of turns mid-work. Nudge for prose rather than
            # leaving the person with nothing. Tools stay enabled: switching
            # them off makes Groq send tool_choice=none, and the model still
            # tries to call one, which it rejects with a 400.
            try:
                closing = await _complete(
                    http,
                    messages
                    + [{
                        "role": "user",
                        "content": "Answer now in prose, using only what the tools returned.",
                    }],
                )
                final_text = (closing.get("content") or "").strip()
            except GroqError:
                pass

        if not final_text:
            # Still nothing to say. Raise so the orchestrator hands the turn to
            # the planner, which always answers from the same Qloo data.
            raise GroqError("model produced no prose after the tool loop")

    # Cards come from whatever Qloo returned, so the UI can never show
    # something the model made up - only something it named.
    seen: dict[str, Entity] = {}
    for bucket in sinks.values():
        seen.update(bucket)
    recommendations = [e for e in seen.values() if prompt.mentioned(final_text, e)]
    session.remember_shown([e.id for e in recommendations])

    return AgentReply(
        message=final_text,
        recommendations=recommendations,
        new_signals=new_signals,
        brain="groq",
        tool_calls=tool_calls,
    )
