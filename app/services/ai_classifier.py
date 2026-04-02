def classify_ticket(issue_description: str, device_type: str, urgency: str):
    text = issue_description.lower()

    if "wifi" in text or "wi-fi" in text or "internet" in text or "network" in text:
        category = "Network"
        summary = "User is experiencing a network-related connectivity or performance issue."
        suggested_steps = [
            "Run ping test to verify connectivity",
            "Run DNS check",
            "Restart network adapter if needed"
        ]
        automation_output = "Ping and DNS diagnostics completed."
    elif "dns" in text:
        category = "DNS"
        summary = "User is experiencing a DNS-related issue."
        suggested_steps = [
            "Run DNS resolution test",
            "Check DNS server settings",
            "Flush DNS cache"
        ]
        automation_output = "DNS diagnostic script completed."
    else:
        category = "General"
        summary = "General IT support issue detected."
        suggested_steps = [
            "Review device status",
            "Collect more details from user",
            "Escalate if issue continues"
        ]
        automation_output = "No automation script matched this issue."

    return {
        "category": category,
        "priority": urgency,
        "summary": summary,
        "suggested_steps": suggested_steps,
        "automation_output": automation_output,
    }