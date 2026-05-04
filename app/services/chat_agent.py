import os
from typing import AsyncGenerator, List, Optional

import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
async_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are ChuggGPT, an expert AI IT helpdesk support engineer.

Your style:
- Be concise and practical — no walls of text
- Give one clear troubleshooting step at a time
- Ask one follow-up question to confirm what happened
- Do not use emojis anywhere in your responses
- If a safe automation can help, include exactly one marker on its own line:
  [AUTOMATION:dns_flush]
  [AUTOMATION:network_reset]
  [AUTOMATION:printer_restart]
  [AUTOMATION:disk_cleanup]
- If the issue is too complex or risky, recommend escalation

At the very end of every reply, on its own line, you MUST include exactly one status marker:
  [STATUS:IN_PROGRESS]   — still troubleshooting, waiting for user response
  [STATUS:RESOLVED]      — user has confirmed the issue is fixed
  [STATUS:ESCALATED]     — issue requires human intervention

Only use [STATUS:RESOLVED] when the user has explicitly confirmed the fix worked.
Only use [STATUS:ESCALATED] when you are recommending human takeover."""


import re

_STATUS_RE = re.compile(r'\[STATUS:(IN_PROGRESS|RESOLVED|ESCALATED)\]', re.IGNORECASE)

def _extract_status(text: str) -> tuple[str, str]:
    match = _STATUS_RE.search(text)
    if match:
        s = match.group(1).upper()
        if s == "RESOLVED":
            return "Resolved", "Resolved"
        if s == "ESCALATED":
            return "Escalated", "Escalated"
    return "In Progress", "Active"

def _strip_status(text: str) -> str:
    return _STATUS_RE.sub("", text).strip()


def _build_history(history) -> List[dict]:
    """Convert ChatMessage ORM objects to Anthropic message format."""
    messages = []
    for msg in history:
        if msg.sender_type == "user":
            messages.append({"role": "user", "content": msg.message})
        elif msg.sender_type in ("agent", "system"):
            messages.append({"role": "assistant", "content": msg.message})
    # Merge consecutive same-role messages
    merged = []
    for m in messages:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["content"] += "\n\n" + m["content"]
        else:
            merged.append(dict(m))
    # Anthropic requires the first message to be user — drop any leading assistant turns
    while merged and merged[0]["role"] == "assistant":
        merged.pop(0)
    return merged


def _format_past_tickets(past_tickets) -> str:
    if not past_tickets:
        return ""
    lines = ["User's recent ticket history:"]
    for t in past_tickets:
        escalated = " [escalated]" if t.ai_escalation_needed else ""
        lines.append(f"  - #{t.id} | {t.category} | {t.status}{escalated}: {t.summary}")
    return "\n".join(lines)


def generate_initial_agent_message(ticket, past_tickets=None) -> str:
    history_block = _format_past_tickets(past_tickets)
    user_prompt = f"""New ticket details:
Device: {ticket.device_type}
Urgency: {ticket.urgency}
Summary: {ticket.summary}
Full description: {ticket.issue_description}
{chr(10) + history_block if history_block else ""}
Acknowledge the issue, give 1-2 immediate troubleshooting steps, and end with a question asking what happened."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        temperature=0.3,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text.strip()


def generate_agent_reply(ticket, user_message: str, history: Optional[List] = None, past_tickets=None) -> dict:
    if user_message.strip().lower() == "escalate":
        return {
            "reply": "Understood. Escalating this ticket to a human administrator now.",
            "new_ticket_status": "Escalated",
            "new_chat_status": "Escalated",
        }

    history_block = _format_past_tickets(past_tickets)
    context = f"""Ticket context:
Device: {ticket.device_type} | Urgency: {ticket.urgency}
Summary: {ticket.summary}
{chr(10) + history_block if history_block else ""}"""

    # Build message history, prefixed with a context message
    messages = []
    if history:
        built = _build_history(history)
        if built:
            # Inject ticket context into the first user turn
            if built[0]["role"] == "user":
                built[0]["content"] = context + "\n\n---\n\n" + built[0]["content"]
            messages = built

    # If no history or history was empty, start fresh
    if not messages:
        messages = [{"role": "user", "content": context + "\n\n---\n\nUser message: " + user_message}]
    else:
        # Append the current user message
        messages.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        temperature=0.3,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    reply = response.content[0].text.strip()
    new_ticket_status, new_chat_status = _extract_status(reply)

    return {
        "reply": _strip_status(reply),
        "new_ticket_status": new_ticket_status,
        "new_chat_status": new_chat_status,
    }


async def stream_agent_reply(ticket, user_message: str, history=None, past_tickets=None) -> AsyncGenerator[dict, None]:
    if user_message.strip().lower() == "escalate":
        msg = "Understood. Escalating this ticket to a human administrator now."
        yield {"type": "token", "content": msg}
        yield {"type": "done", "reply": msg, "new_ticket_status": "Escalated", "new_chat_status": "Escalated"}
        return

    history_block = _format_past_tickets(past_tickets)
    context = f"Ticket context:\nDevice: {ticket.device_type} | Urgency: {ticket.urgency}\nSummary: {ticket.summary}" + (f"\n\n{history_block}" if history_block else "")

    messages = []
    if history:
        built = _build_history(history)
        if built:
            if built[0]["role"] == "user":
                built[0]["content"] = context + "\n\n---\n\n" + built[0]["content"]
            messages = built

    if not messages:
        messages = [{"role": "user", "content": context + "\n\n---\n\nUser message: " + user_message}]
    else:
        messages.append({"role": "user", "content": user_message})

    full_text = ""
    async with async_client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=512,
        temperature=0.3,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            full_text += text
            yield {"type": "token", "content": text}

    new_ticket_status, new_chat_status = _extract_status(full_text)
    yield {"type": "done", "reply": full_text, "new_ticket_status": new_ticket_status, "new_chat_status": new_chat_status}
