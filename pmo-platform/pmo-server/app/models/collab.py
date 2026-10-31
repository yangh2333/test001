"""协同域模型（M6）。"""
from datetime import datetime
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Date, Text, JSON,
    ForeignKey, Numeric, SmallInteger,
)
from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin, SoftDeleteMixin


class Ticket(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "ticket"
    code = Column(String(64), nullable=False, unique=True)
    title = Column(String(200), nullable=False)
    ticket_type = Column(String(16), nullable=False)
    project_id = Column(BigInteger)
    requester_user_id = Column(BigInteger, nullable=False)
    target_dept_id = Column(BigInteger, nullable=False)
    target_user_id = Column(BigInteger)
    description = Column(Text, nullable=False)
    priority = Column(SmallInteger, default=3)
    status = Column(String(16), default="pending")
    sla_due_at = Column(DateTime, nullable=False)
    responded_at = Column(DateTime)
    resolved_at = Column(DateTime)
    escalate_level = Column(SmallInteger, default=0)
    satisfaction_score = Column(SmallInteger)
    closed_by = Column(BigInteger)
    close_comment = Column(Text)


class TicketAction(IdMixin, Base):
    __tablename__ = "ticket_action"
    ticket_id = Column(BigInteger, nullable=False)
    actor_user_id = Column(BigInteger, nullable=False)
    action = Column(String(32), nullable=False)
    from_status = Column(String(16))
    to_status = Column(String(16))
    comment = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class Meeting(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "meeting"
    project_id = Column(BigInteger)
    title = Column(String(200), nullable=False)
    start_at = Column(DateTime, nullable=False)
    attendees = Column(JSON)
    minutes_url = Column(String(512))
    created_by = Column(BigInteger)


class MeetingDecision(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "meeting_decision"
    meeting_id = Column(BigInteger, nullable=False)
    content = Column(Text, nullable=False)
    owner_user_id = Column(BigInteger, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String(16), default="open")
    todo_id = Column(BigInteger)


class WeeklyReport(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "weekly_report"
    project_id = Column(BigInteger, nullable=False)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    auto_content = Column(JSON, default=dict)
    ai_summary = Column(Text)
    pm_comment = Column(Text)
    risk_supplement = Column(Text)
    status = Column(String(16), default="draft")
    published_at = Column(DateTime)
    published_by = Column(BigInteger)


class TodoItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "todo_item"
    user_id = Column(BigInteger, nullable=False)
    kind = Column(String(16), nullable=False)
    ref_type = Column(String(32), nullable=False)
    ref_id = Column(BigInteger, nullable=False)
    title = Column(String(200), nullable=False)
    due_at = Column(DateTime)
    status = Column(String(16), default="open")
    priority_score = Column(Numeric(6, 2), default=0)
    source_channel = Column(String(16), default="system")
    done_at = Column(DateTime)


class Notification(IdMixin, TimestampMixin, Base):
    __tablename__ = "notification"
    user_id = Column(BigInteger, nullable=False)
    channel = Column(String(16), nullable=False)
    event_type = Column(String(64), nullable=False)
    payload = Column(JSON, default=dict)
    status = Column(String(16), default="pending")
    dedup_key = Column(String(128))
    sent_at = Column(DateTime)
    fail_reason = Column(Text)
    retry_count = Column(SmallInteger, default=0)


class NotificationRule(IdMixin, TimestampMixin, Base):
    __tablename__ = "notification_rule"
    event_type = Column(String(64), nullable=False)
    channels = Column(JSON, default=list)
    freq_limit = Column(String(32), default="realtime")
    user_override = Column(JSON)
    enabled = Column(Boolean, default=True)
