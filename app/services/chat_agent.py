import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_initial_agent_message(ticket):
    prompt = f"""
You are ChuggGPT, an AI IT helpdesk support engineer built to diagnose and resolve IT issues efficiently.

Your goal:
- help the user fix the issue step by step
- do NOT dump a giant list
- start with a short acknowledgement
- give 1–2 troubleshooting steps
- end with a question asking what happened

Ticket Summary:
{ticket.summary}

Device:
{ticket.device_type}

Urgency:
{ticket.urgency}

Issue Description:
{ticket.issue_description}

Allowed automation markers:
[AUTOMATION:network_reset]
[AUTOMATION:dns_flush]
[AUTOMATION:printer_restart]
[AUTOMATION:disk_cleanup]
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert IT helpdesk support engineer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    return response.choices[0].message.content.strip()


def generate_agent_reply(ticket, user_message: str):
    lowered = user_message.lower()

    if lowered.strip() == "escalate":
        return {
            "reply": "Understood. Escalating this issue to a human administrator.",
            "new_ticket_status": "Escalated",
            "new_chat_status": "Escalated",
        }

    prompt = f"""
You are an IT support AI continuing a troubleshooting conversation.

Ticket summary:
{ticket.summary}

Device:
{ticket.device_type}

Urgency:
{ticket.urgency}

User message:
{user_message}

Give the next best troubleshooting step.
Be concise and practical.
Ask one follow-up question.

Allowed automation markers:
[AUTOMATION:network_reset]
[AUTOMATION:dns_flush]
[AUTOMATION:printer_restart]
[AUTOMATION:disk_cleanup]
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert IT helpdesk support engineer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    reply = response.choices[0].message.content.strip()

    lower_reply = reply.lower()

    if "resolved" in lower_reply or "fixed" in lower_reply:
        new_ticket_status = "Resolved"
        new_chat_status = "Resolved"
    else:
        new_ticket_status = "In Progress"
        new_chat_status = "Active"

    return {
        "reply": reply,
        "new_ticket_status": new_ticket_status,
        "new_chat_status": new_chat_status
    }