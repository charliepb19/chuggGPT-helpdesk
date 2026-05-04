import json
import os
from typing import Any, Dict

import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are an AI triage engine for an IT helpdesk platform called ChuggGPT.

Your job:
- classify the helpdesk issue
- estimate severity/priority
- estimate business impact
- estimate confidence
- decide whether automation is appropriate
- recommend a safe automation if applicable
- decide whether escalation to a human is needed
- provide a short troubleshooting plan

Return ONLY valid JSON in this exact schema:

{
  "predicted_issue_type": "string",
  "predicted_priority": "Low|Medium|High|Critical",
  "business_impact": "single_user|multi_user|team_wide|org_wide",
  "confidence_score": 0.0,
  "automation_eligible": true,
  "suggested_automation": "dns_flush",
  "recommended_script": "dns_flush",
  "escalation_needed": false,
  "escalation_reason": "",
  "summary": "short summary",
  "suggested_steps": [
    "step 1",
    "step 2",
    "step 3"
  ]
}

Rules:
- confidence_score must be between 0.0 and 1.0
- if unsure, lower confidence
- if the issue affects many users or business-critical systems, escalation_needed should usually be true
- if the user has had the same or similar issue before (visible in ticket history), increase severity and strongly consider escalation_needed=true
- if a recurring issue has been resolved before, note that in the summary
- only suggest realistic IT helpdesk automations
- if no automation is appropriate, set automation_eligible false and suggested_automation to null
- recommended_script should usually match the automation name if one exists
- return JSON only, no markdown, no explanation"""

_FALLBACK = {
    "predicted_issue_type": "General",
    "predicted_priority": "Medium",
    "business_impact": "single_user",
    "confidence_score": 0.25,
    "automation_eligible": False,
    "suggested_automation": None,
    "recommended_script": None,
    "escalation_needed": True,
    "escalation_reason": "Model returned invalid JSON.",
    "summary": "Manual review recommended.",
    "suggested_steps": [
        "Review the ticket manually",
        "Ask the user for more details",
        "Escalate if the issue appears broad or high impact",
    ],
}


def _format_past_tickets(past_tickets) -> str:
    if not past_tickets:
        return ""
    lines = ["User's recent ticket history (use this to detect recurring issues and adjust severity):"]
    for t in past_tickets:
        escalated = " [was escalated]" if t.ai_escalation_needed else ""
        lines.append(f"  - #{t.id} | {t.category} | {t.status}{escalated}: {t.summary}")
    return "\n".join(lines)


def triage_ticket(issue_description: str, device_type: str, urgency: str, past_tickets=None) -> Dict[str, Any]:
    history_block = _format_past_tickets(past_tickets)
    user_prompt = f"""Device type: {device_type}
Urgency: {urgency}
Issue description: {issue_description}
{chr(10) + history_block if history_block else ""}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        temperature=0.2,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = dict(_FALLBACK)

    if not isinstance(parsed.get("confidence_score"), (int, float)):
        parsed["confidence_score"] = 0.25

    parsed["confidence_score"] = max(0.0, min(1.0, float(parsed["confidence_score"])))
    parsed["_raw_model_output"] = raw
    return parsed
