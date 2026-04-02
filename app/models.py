from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float
from datetime import datetime, timezone
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    name = Column(String, nullable=False)
    device_type = Column(String, nullable=False)
    urgency = Column(String, nullable=False)
    issue_description = Column(Text, nullable=False)

    category = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    suggested_steps = Column(Text, nullable=True)

    automation_possible = Column(Boolean, default=False)
    recommended_script = Column(String, nullable=True)
    automation_output = Column(Text, nullable=True)

    status = Column(String, default="Open")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # New AI foundation fields
    ai_confidence = Column(Float, default=0.0)
    ai_business_impact = Column(String, nullable=True)
    ai_escalation_needed = Column(Boolean, default=False)
    ai_escalation_reason = Column(Text, nullable=True)
    ai_suggested_automation = Column(String, nullable=True)
    ai_raw_output = Column(Text, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, nullable=True)
    action = Column(String, nullable=False)
    details = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="Active", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    sender_type = Column(String, nullable=False)  # user, agent, system
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TicketPrediction(Base):
    __tablename__ = "ticket_predictions"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)

    predicted_issue_type = Column(String, nullable=True)
    predicted_priority = Column(String, nullable=True)
    business_impact = Column(String, nullable=True)
    confidence_score = Column(Float, default=0.0)

    automation_eligible = Column(Boolean, default=False)
    suggested_automation = Column(String, nullable=True)
    recommended_script = Column(String, nullable=True)

    escalation_needed = Column(Boolean, default=False)
    escalation_reason = Column(Text, nullable=True)

    summary = Column(Text, nullable=True)
    suggested_steps = Column(Text, nullable=True)
    raw_model_output = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AutomationRun(Base):
    __tablename__ = "automation_runs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)

    automation_name = Column(String, nullable=False)
    triggered_by = Column(String, default="system")  # ai, admin, user, system
    risk_level = Column(String, default="low")
    requires_confirmation = Column(Boolean, default=False)

    status = Column(String, default="pending")  # pending, running, success, failed, blocked
    output_log = Column(Text, nullable=True)

    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)