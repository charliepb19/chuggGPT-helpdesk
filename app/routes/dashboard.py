from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ticket, User, ChatSession, ChatMessage, TicketPrediction, AutomationRun
from app.services.automation import get_dashboard_data, add_audit_log, execute_automation

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    return db.query(User).filter(User.id == user_id).first()


def require_admin(request: Request, db: Session):
    user = get_current_user(request, db)

    if not user:
        return None

    if user.role != "admin":
        return None

    return user


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    search_name: str = Query(default=""),
    status_filter: str = Query(default=""),
    category_filter: str = Query(default=""),
    severity_filter: str = Query(default="")
):
    admin_user = require_admin(request, db)
    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    data = get_dashboard_data(
        db,
        search_name=search_name,
        status_filter=status_filter,
        category_filter=category_filter,
        severity_filter=severity_filter
    )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "current_user": admin_user,
            "category_counts": data["category_counts"],
            "severity_counts": data["severity_counts"],
            "status_counts": data["status_counts"],
            "tickets": data["tickets"],
            "total_tickets": data["total_tickets"],
            "filtered_ticket_count": data["filtered_ticket_count"],
            "automation_possible_count": data["automation_possible_count"],
            "assigned_count": data["assigned_count"],
            "audit_logs": data["audit_logs"],
            "all_categories": data["all_categories"],
            "all_severities": data["all_severities"],
            "all_statuses": data["all_statuses"],
            "admin_users": data["admin_users"],
            "search_name": search_name,
            "status_filter": status_filter,
            "category_filter": category_filter,
            "severity_filter": severity_filter,
        }
    )


@router.post("/update-ticket-status")
def update_ticket_status(
    request: Request,
    ticket_id: int = Form(...),
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    admin_user = require_admin(request, db)
    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if ticket:
        old_status = ticket.status
        ticket.status = status
        db.commit()

        add_audit_log(
            db=db,
            action="Status Updated",
            details=f"Ticket status changed from {old_status} to {status}.",
            ticket_id=ticket.id
        )

    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/assign-ticket")
def assign_ticket(
    request: Request,
    ticket_id: int = Form(...),
    assignee_id: int = Form(...),
    db: Session = Depends(get_db)
):
    admin_user = require_admin(request, db)
    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    assignee = db.query(User).filter(User.id == assignee_id).first()

    if ticket and assignee:
        ticket.assigned_to_user_id = assignee.id
        db.commit()

        add_audit_log(
            db=db,
            action="Ticket Assigned",
            details=f"Ticket assigned to {assignee.name}.",
            ticket_id=ticket.id
        )

    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/claim-ticket")
def claim_ticket(
    request: Request,
    ticket_id: int = Form(...),
    db: Session = Depends(get_db)
):
    admin_user = require_admin(request, db)
    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if ticket:
        ticket.assigned_to_user_id = admin_user.id
        db.commit()

        add_audit_log(
            db=db,
            action="Ticket Claimed",
            details=f"Ticket claimed by {admin_user.name}.",
            ticket_id=ticket.id
        )

    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/unassign-ticket")
def unassign_ticket(
    request: Request,
    ticket_id: int = Form(...),
    db: Session = Depends(get_db)
):
    admin_user = require_admin(request, db)
    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if ticket:
        ticket.assigned_to_user_id = None
        db.commit()

        add_audit_log(
            db=db,
            action="Ticket Unassigned",
            details="Ticket was removed from its assignee.",
            ticket_id=ticket.id
        )

    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/delete-ticket")
def delete_ticket(
    request: Request,
    ticket_id: int = Form(...),
    db: Session = Depends(get_db)
):
    admin_user = require_admin(request, db)
    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if ticket:
        ticket_name = ticket.name

        add_audit_log(
            db=db,
            action="Ticket Deleted",
            details=f"Resolved ticket for {ticket_name} was deleted from the dashboard.",
            ticket_id=ticket.id
        )

        # Delete child records before the ticket (foreign key order matters)
        sessions = db.query(ChatSession).filter(ChatSession.ticket_id == ticket.id).all()
        for session in sessions:
            db.query(ChatMessage).filter(ChatMessage.chat_session_id == session.id).delete()
        db.query(ChatSession).filter(ChatSession.ticket_id == ticket.id).delete()
        db.query(TicketPrediction).filter(TicketPrediction.ticket_id == ticket.id).delete()
        db.query(AutomationRun).filter(AutomationRun.ticket_id == ticket.id).delete()

        db.delete(ticket)
        db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/execute-automation")
def run_automation(
    request: Request,
    ticket_id: int = Form(...),
    db: Session = Depends(get_db)
):
    admin_user = require_admin(request, db)
    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    execute_automation(db, ticket_id)
    return RedirectResponse(url="/dashboard", status_code=303)