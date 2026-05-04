from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models import User, Ticket, AuditLog
from app.services.ai_classifier import classify_ticket
from app.services.ai_triage import triage_ticket
from app.services.automation import save_ticket

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    return db.query(User).filter(User.id == user_id).first()


@router.get("/submit", response_class=HTMLResponse)
def show_submit_alias(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request,
        "submit_ticket.html",
        {"request": request, "current_user": user}
    )


@router.get("/submit-ticket", response_class=HTMLResponse)
def show_submit_ticket(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request,
        "submit_ticket.html",
        {"request": request, "current_user": user}
    )


@router.get("/my-tickets", response_class=HTMLResponse)
def my_tickets_page(
    request: Request,
    db: Session = Depends(get_db),
    status_filter: str = Query(default=""),
    category_filter: str = Query(default=""),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    query = db.query(Ticket).filter(Ticket.user_id == user.id)
    if status_filter:
        query = query.filter(Ticket.status == status_filter)
    if category_filter:
        query = query.filter(Ticket.category == category_filter)
    tickets = query.order_by(Ticket.id.desc()).all()

    all_tickets = db.query(Ticket).filter(Ticket.user_id == user.id).all()
    all_statuses = sorted({t.status for t in all_tickets if t.status})
    all_categories = sorted({t.category for t in all_tickets if t.category})

    return templates.TemplateResponse(
        request,
        "my_tickets.html",
        {
            "request": request,
            "current_user": user,
            "tickets": tickets,
            "all_statuses": all_statuses,
            "all_categories": all_categories,
            "status_filter": status_filter,
            "category_filter": category_filter,
        }
    )


@router.post("/submit-ticket", response_class=HTMLResponse)
@limiter.limit("10/minute")
def submit_ticket(
    request: Request,
    device_type: str = Form(..., max_length=100),
    urgency: str = Form(..., max_length=50),
    issue_description: str = Form(..., max_length=3000),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    past_tickets = (
        db.query(Ticket)
        .filter(Ticket.user_id == user.id)
        .order_by(Ticket.id.desc())
        .limit(5)
        .all()
    )

    # Keep your current classifier as a fallback / compatibility layer
    base_result = classify_ticket(issue_description, device_type, urgency)

    # Try the new structured AI triage first
    try:
        triage = triage_ticket(issue_description, device_type, urgency, past_tickets=past_tickets)
    except Exception:
        triage = {
            "predicted_issue_type": base_result.get("category", "General"),
            "predicted_priority": base_result.get("priority", "Medium"),
            "business_impact": "single_user",
            "confidence_score": 0.50,
            "automation_eligible": base_result.get("automation_possible", False),
            "suggested_automation": base_result.get("recommended_script"),
            "recommended_script": base_result.get("recommended_script"),
            "escalation_needed": False,
            "escalation_reason": "",
            "summary": base_result.get("summary", "No summary available."),
            "suggested_steps": base_result.get("suggested_steps", ["Review issue manually"]),
            "_raw_model_output": "Fallback to classify_ticket()",
        }

    suggested_steps_value = triage.get("suggested_steps", base_result.get("suggested_steps", "No suggested steps available."))
    if isinstance(suggested_steps_value, list):
        suggested_steps_value = "\n".join(suggested_steps_value)

    ticket_data = {
        "user_id": user.id,
        "name": user.name,
        "device_type": device_type,
        "urgency": urgency,
        "issue_description": issue_description,
        "category": triage.get("predicted_issue_type", base_result.get("category", "General")),
        "severity": triage.get("predicted_priority", base_result.get("priority", "Medium")),
        "summary": triage.get("summary", base_result.get("summary", "No summary available.")),
        "suggested_steps": suggested_steps_value,
        "automation_possible": triage.get("automation_eligible", base_result.get("automation_possible", False)),
        "recommended_script": triage.get("recommended_script", base_result.get("recommended_script", "None")),
        "automation_output": "No automation output.",
        "status": "Open",

        # New AI fields
        "ai_confidence": triage.get("confidence_score", 0.0),
        "ai_business_impact": triage.get("business_impact"),
        "ai_escalation_needed": triage.get("escalation_needed", False),
        "ai_escalation_reason": triage.get("escalation_reason", ""),
        "ai_suggested_automation": triage.get("suggested_automation"),
        "ai_raw_output": triage.get("_raw_model_output", ""),
    }

    ticket = save_ticket(db, ticket_data, triage_data=triage)

    return RedirectResponse(url=f"/chat/{ticket.id}", status_code=303)


@router.get("/ticket/{ticket_id}", response_class=HTMLResponse)
def ticket_detail(ticket_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return RedirectResponse(url="/my-tickets", status_code=303)

    if user.role != "admin" and ticket.user_id != user.id:
        return RedirectResponse(url="/my-tickets", status_code=303)

    audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.ticket_id == ticket_id)
        .order_by(AuditLog.id.desc())
        .all()
    )

    assignee = None
    if ticket.assigned_to_user_id:
        assignee = db.query(User).filter(User.id == ticket.assigned_to_user_id).first()

    return templates.TemplateResponse(
        request,
        "ticket_detail.html",
        {
            "request": request,
            "current_user": user,
            "ticket": ticket,
            "audit_logs": audit_logs,
            "assignee": assignee,
        }
    )