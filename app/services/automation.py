import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import Ticket, AuditLog, User, ChatSession, ChatMessage, TicketPrediction, AutomationRun
from app.services.chat_agent import generate_initial_agent_message
from app.services.automation_policy import get_automation_policy


def add_audit_log(db: Session, action: str, details: str, ticket_id: int | None = None):
    log = AuditLog(
        ticket_id=ticket_id,
        action=action,
        details=details
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def extract_automation_marker(text: str):
    match = re.search(r"\[AUTOMATION:([a-z_]+)\]", text)
    if not match:
        return None
    return match.group(1)


def remove_automation_marker(text: str):
    return re.sub(r"\s*\[AUTOMATION:[a-z_]+\]\s*", "", text).strip()


def create_automation_run(
    db: Session,
    ticket: Ticket,
    automation_name: str,
    triggered_by: str,
    status: str,
    output_log: str
):
    policy = get_automation_policy(automation_name)

    run = AutomationRun(
        ticket_id=ticket.id,
        automation_name=automation_name,
        triggered_by=triggered_by,
        risk_level=policy["risk_level"],
        requires_confirmation=policy["requires_confirmation"],
        status=status,
        output_log=output_log,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc) if status in ["success", "failed", "blocked"] else None,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def run_named_automation(db: Session, ticket: Ticket, automation_name: str, triggered_by: str = "system"):
    policy = get_automation_policy(automation_name)

    if policy["requires_confirmation"] and triggered_by == "ai":
        output = f"Automation '{automation_name}' blocked pending confirmation due to {policy['risk_level']} risk policy."
        ticket.automation_output = output
        db.commit()
        db.refresh(ticket)

        create_automation_run(
            db=db,
            ticket=ticket,
            automation_name=automation_name,
            triggered_by=triggered_by,
            status="blocked",
            output_log=output
        )

        add_audit_log(
            db=db,
            action="Automation Blocked",
            details=output,
            ticket_id=ticket.id
        )
        return output

    if automation_name == "network_reset":
        output = "Simulated action: Reset network adapter and ran connectivity diagnostics."
    elif automation_name == "dns_flush":
        output = "Simulated action: Flushed DNS cache and ran DNS resolution checks."
    elif automation_name == "printer_restart":
        output = "Simulated action: Restarted printer spooler service and cleared print queue."
    elif automation_name == "disk_cleanup":
        output = "Simulated action: Ran temporary file cleanup analysis and disk usage check."
    elif automation_name == "password_reset":
        output = "Simulated action: Password reset workflow requires admin confirmation in production."
    elif automation_name == "restart_service":
        output = "Simulated action: Restart service workflow completed in simulation mode."
    else:
        output = f"Simulated action: Unknown automation '{automation_name}' was requested."

    ticket.automation_output = output
    db.commit()
    db.refresh(ticket)

    create_automation_run(
        db=db,
        ticket=ticket,
        automation_name=automation_name,
        triggered_by=triggered_by,
        status="success",
        output_log=output
    )

    add_audit_log(
        db=db,
        action="Automation Executed",
        details=output,
        ticket_id=ticket.id
    )

    return output


def create_chat_session_for_ticket(db: Session, ticket: Ticket):
    # Reuse existing session if one already exists for this ticket
    existing_session = (
        db.query(ChatSession)
        .filter(ChatSession.ticket_id == ticket.id)
        .order_by(ChatSession.id.desc())
        .first()
    )

    if existing_session:
        return existing_session

    session = ChatSession(
        ticket_id=ticket.id,
        user_id=ticket.user_id,
        status="Active"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    initial_message_raw = generate_initial_agent_message(ticket)
    automation_name = extract_automation_marker(initial_message_raw)
    initial_message = remove_automation_marker(initial_message_raw)

    message = ChatMessage(
        chat_session_id=session.id,
        sender_type="agent",
        message=initial_message
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    if automation_name:
        automation_output = run_named_automation(db, ticket, automation_name, triggered_by="agent")
        system_message = ChatMessage(
            chat_session_id=session.id,
            sender_type="system",
            message=f"Automation result: {automation_output}"
        )
        db.add(system_message)
        db.commit()

    add_audit_log(
        db=db,
        action="Chat Session Started",
        details="AI support chat was started for this ticket.",
        ticket_id=ticket.id
    )

    return session


def save_ticket(db: Session, ticket_data: dict, triage_data: dict | None = None):
    ticket = Ticket(**ticket_data)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    add_audit_log(
        db=db,
        action="Ticket Submitted",
        details=f"Ticket submitted by {ticket.name} for {ticket.device_type} with urgency {ticket.urgency}.",
        ticket_id=ticket.id
    )

    if triage_data:
        prediction = TicketPrediction(
            ticket_id=ticket.id,
            predicted_issue_type=triage_data.get("predicted_issue_type"),
            predicted_priority=triage_data.get("predicted_priority"),
            business_impact=triage_data.get("business_impact"),
            confidence_score=triage_data.get("confidence_score", 0.0),
            automation_eligible=triage_data.get("automation_eligible", False),
            suggested_automation=triage_data.get("suggested_automation"),
            recommended_script=triage_data.get("recommended_script"),
            escalation_needed=triage_data.get("escalation_needed", False),
            escalation_reason=triage_data.get("escalation_reason"),
            summary=triage_data.get("summary"),
            suggested_steps="\n".join(triage_data.get("suggested_steps", []))
            if isinstance(triage_data.get("suggested_steps"), list)
            else str(triage_data.get("suggested_steps", "")),
            raw_model_output=triage_data.get("_raw_model_output", ""),
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)

        add_audit_log(
            db=db,
            action="AI Triage Completed",
            details=(
                f"Issue={triage_data.get('predicted_issue_type')}, "
                f"Priority={triage_data.get('predicted_priority')}, "
                f"Confidence={triage_data.get('confidence_score')}, "
                f"Business Impact={triage_data.get('business_impact')}, "
                f"Suggested Automation={triage_data.get('suggested_automation')}"
            ),
            ticket_id=ticket.id
        )

        suggested_automation = triage_data.get("suggested_automation")
        automation_eligible = triage_data.get("automation_eligible", False)
        confidence_score = triage_data.get("confidence_score", 0.0)

        if suggested_automation and automation_eligible and confidence_score >= 0.85:
            output = run_named_automation(db, ticket, suggested_automation, triggered_by="ai")

            add_audit_log(
                db=db,
                action="AI Automation Attempted",
                details=f"AI attempted automation '{suggested_automation}'. Result: {output}",
                ticket_id=ticket.id
            )

    create_chat_session_for_ticket(db, ticket)

    return ticket


def get_all_tickets(db: Session):
    return db.query(Ticket).order_by(Ticket.id.desc()).all()


def get_recent_audit_logs(db: Session, limit: int = 20):
    return db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()


def get_user_name_by_id(db: Session, user_id: int | None):
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    return user.name if user else None


def execute_automation(db: Session, ticket_id: int):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        return None

    if not ticket.automation_possible:
        output = "Automation not available for this ticket."
        ticket.automation_output = output
        db.commit()

        create_automation_run(
            db=db,
            ticket=ticket,
            automation_name=ticket.recommended_script or "unknown",
            triggered_by="admin",
            status="failed",
            output_log=output
        )

        add_audit_log(
            db=db,
            action="Automation Attempted",
            details="Automation was attempted, but this ticket was not marked as automation-possible.",
            ticket_id=ticket.id
        )
        return ticket

    script_name = (ticket.recommended_script or "").lower()

    if "dns" in script_name:
        automation_name = "dns_flush"
    elif "network" in script_name:
        automation_name = "network_reset"
    elif "disk" in script_name:
        automation_name = "disk_cleanup"
    elif "printer" in script_name:
        automation_name = "printer_restart"
    elif "password" in script_name:
        automation_name = "password_reset"
    else:
        automation_name = ticket.recommended_script or "custom_workflow"

    output = run_named_automation(db, ticket, automation_name, triggered_by="admin")
    return ticket


def get_dashboard_data(
    db: Session,
    search_name: str = "",
    status_filter: str = "",
    category_filter: str = "",
    severity_filter: str = ""
):
    query = db.query(Ticket)

    if search_name:
        query = query.filter(Ticket.name.ilike(f"%{search_name}%"))

    if status_filter:
        query = query.filter(Ticket.status == status_filter)

    if category_filter:
        query = query.filter(Ticket.category == category_filter)

    if severity_filter:
        query = query.filter(Ticket.severity == severity_filter)

    tickets = query.order_by(Ticket.id.desc()).all()
    audit_logs = get_recent_audit_logs(db)

    all_tickets = db.query(Ticket).all()

    category_counts = {}
    severity_counts = {}
    status_counts = {
        "Open": 0,
        "In Progress": 0,
        "Resolved": 0,
        "Escalated": 0,
    }

    automation_possible_count = 0
    assigned_count = 0
    ai_escalation_count = 0

    enriched_tickets = []
    for ticket in tickets:
        ticket.assigned_to_name = get_user_name_by_id(db, ticket.assigned_to_user_id)
        enriched_tickets.append(ticket)

    for ticket in all_tickets:
        category = ticket.category or "Unknown"
        severity = ticket.severity or "Unknown"
        status = ticket.status or "Open"

        category_counts[category] = category_counts.get(category, 0) + 1
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1

        if ticket.automation_possible:
            automation_possible_count += 1

        if ticket.assigned_to_user_id:
            assigned_count += 1

        if ticket.ai_escalation_needed:
            ai_escalation_count += 1

    all_categories = sorted({ticket.category for ticket in all_tickets if ticket.category})
    all_severities = sorted({ticket.severity for ticket in all_tickets if ticket.severity})
    all_statuses = ["Open", "In Progress", "Resolved", "Escalated"]

    return {
        "category_counts": category_counts,
        "severity_counts": severity_counts,
        "status_counts": status_counts,
        "tickets": enriched_tickets,
        "total_tickets": len(all_tickets),
        "filtered_ticket_count": len(enriched_tickets),
        "automation_possible_count": automation_possible_count,
        "assigned_count": assigned_count,
        "ai_escalation_count": ai_escalation_count,
        "audit_logs": audit_logs,
        "all_categories": all_categories,
        "all_severities": all_severities,
        "all_statuses": all_statuses,
    }