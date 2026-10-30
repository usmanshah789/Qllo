"""Claude-backed brain.

Claude decides when to ask, when to call Qloo and what to say. Qloo stays the
only source of taste data — the prompt forbids inventing recommendations, and
the cards shown in the UI are built from the entities Qloo actually returned,
not from the model's prose.
"""

import json

from anthropic import AsyncAnthropic

from app import config
from app.agent import prompt, signals, tools
from app.agent.base import AgentReply, ToolCall
from app.qloo.models import Entity
from app.storage.models import Session

MAX_TURNS = 6

async def respond(session: Session, text: str) -> AgentReply:
    client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

    system = prompt.system_prompt(session)
    messages: list[dict] = prompt.history(session) + [{"role": "user", "content": text}]

    sinks: dict[str, dict[str, Entity]] = {}
    new_signals = []
    tool_calls: list[ToolCall] = []
    final_text = ""

    for _ in range(MAX_TURNS):
        response = await client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=800,
            system=system,
            tools=tools.TOOL_SCHEMAS,
            messages=messages,
        )

        text_parts = [b.text for b in response.content if b.type == "text"]
        if text_parts:
            final_text = "\n".join(text_parts).strip()

        if response.stop_reason != "tool_use":
            break

        messages.append({"role": "assistant", "content": response.content})

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            known_before = set(sinks.get(block.name, {}))
            payload = await tools.run_tool(
                block.name,
                block.input,
                sinks=sinks,
                exclude_ids=session.shown_entity_ids + session.profile.disliked_entity_ids(),
            )
            if block.name == "search_entity":
                fresh = [
                    entity
                    for key, entity in sinks.get(block.name, {}).items()
                    if key not in known_before
                ]
                for entity in fresh[:1]:
                    signal = signals.record_lookup(
                        session, dict(block.input).get("query", ""), entity,
                        said_by_user=text,
                    )
                    if signal:
                        new_signals.append(signal)

            count = len(payload.get("results", [])) if isinstance(payload, dict) else 0
            tool_calls.append(
                ToolCall(
                    name=block.name,
                    arguments=dict(block.input),
                    result_summary=payload.get("error") or f"{count} results",
                )
            )
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(payload)[:6000],
            })

        messages.append({"role": "user", "content": results})

    # Cards come from whatever Qloo returned, so the UI can never show
    # something the model made up - only something it named.
    seen: dict[str, Entity] = {}
    for bucket in sinks.values():
        seen.update(bucket)
    recommendations = [e for e in seen.values() if prompt.mentioned(final_text, e)]
    session.remember_shown([e.id for e in recommendations])

    return AgentReply(
        message=final_text or "I lost my thread there — say that again?",
        recommendations=recommendations,
        new_signals=new_signals,
        brain="claude",
        tool_calls=tool_calls,
    )
