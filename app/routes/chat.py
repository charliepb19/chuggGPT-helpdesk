from fastapi import APIRouter, Request, Depends, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models import User, Ticket, ChatSession, ChatMessage
from app.services.chat_agent import generate_agent_reply
from app.services.automation import (
    add_audit_log,
    extract_automation_marker,
    remove_automation_marker,
    run_named_automation,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_current_user_from_request(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


@router.get("/chat/{ticket_id}", response_class=HTMLResponse)
def chat_page(ticket_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return RedirectResponse(url="/my-tickets", status_code=303)

    if user.role != "admin" and ticket.user_id != user.id:
        return RedirectResponse(url="/my-tickets", status_code=303)

    chat_session = db.query(ChatSession).filter(ChatSession.ticket_id == ticket.id).first()
    if not chat_session:
        return RedirectResponse(url="/my-tickets", status_code=303)

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_session_id == chat_session.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "chat.html",
        {
            "request": request,
            "current_user": user,
            "ticket": ticket,
            "chat_session": chat_session,
            "messages": messages,
        }
    )


@router.websocket("/ws/chat/{ticket_id}")
async def chat_websocket(websocket: WebSocket, ticket_id: int, user_id: int = Query(...)):
    await websocket.accept()
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.send_json({"type": "error", "message": "Not authenticated. Please log in again."})
            await websocket.close()
            return

        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            await websocket.send_json({"type": "error", "message": "Ticket not found."})
            await websocket.close()
            return

        if user.role != "admin" and ticket.user_id != user.id:
            await websocket.send_json({"type": "error", "message": "Access denied."})
            await websocket.close()
            return

        chat_session = db.query(ChatSession).filter(ChatSession.ticket_id == ticket.id).first()
        if not chat_session:
            await websocket.send_json({"type": "error", "message": "Chat session not found."})
            await websocket.close()
            return

        while True:
            user_text = (await websocket.receive_text()).strip()
            if not user_text:
                continue

            db.refresh(ticket)
            db.refresh(chat_session)

            if chat_session.status in {"Resolved", "Escalated"}:
                await websocket.send_json(
                    {"type": "system", "message": f"This chat session is {chat_session.status}."}
                )
                continue

            user_msg = ChatMessage(
                chat_session_id=chat_session.id,
                sender_type="user",
                message=user_text
            )
            db.add(user_msg)
            db.commit()
            db.refresh(user_msg)

            await websocket.send_json(
                {"type": "message", "sender_type": "user", "message": user_msg.message}
            )

            agent_result = generate_agent_reply(ticket, user_text)
            raw_reply = agent_result["reply"]

            automation_name = extract_automation_marker(raw_reply)
            clean_reply = remove_automation_marker(raw_reply)

            agent_msg = ChatMessage(
                chat_session_id=chat_session.id,
                sender_type="agent",
                message=clean_reply
            )
            db.add(agent_msg)

            ticket.status = agent_result["new_ticket_status"]
            chat_session.status = agent_result["new_chat_status"]

            db.commit()
            db.refresh(agent_msg)
            db.refresh(ticket)
            db.refresh(chat_session)

            add_audit_log(
                db=db,
                action="Chat Updated",
                details=f"AI chat responded and ticket status is now {ticket.status}.",
                ticket_id=ticket.id
            )

            await websocket.send_json(
                {"type": "message", "sender_type": "agent", "message": agent_msg.message}
            )

            if automation_name:
                automation_output = run_named_automation(db, ticket, automation_name, triggered_by="agent")

                system_msg = ChatMessage(
                    chat_session_id=chat_session.id,
                    sender_type="system",
                    message=f"Automation result: {automation_output}"
                )
                db.add(system_msg)
                db.commit()
                db.refresh(system_msg)

                await websocket.send_json(
                    {"type": "message", "sender_type": "system", "message": system_msg.message}
                )

                add_audit_log(
                    db=db,
                    action="Chat Automation Executed",
                    details=f"Automation '{automation_name}' was triggered during chat.",
                    ticket_id=ticket.id
                )

            await websocket.send_json(
                {
                    "type": "status_update",
                    "ticket_status": ticket.status,
                    "chat_status": chat_session.status
                }
            )

    except WebSocketDisconnect:
        pass
    finally:
        db.close()