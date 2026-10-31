"""风险域模型（M5，P2）。"""
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Date, Text, JSON,
    ForeignKey, SmallInteger,
)
from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin, SoftDeleteMixin


class Risk(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "risk"
    project_id = Column(BigInteger, nullable=False)
    code = Column(String(64), nullable=False, unique=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    probability = Column(SmallInteger, default=3)
    impact = Column(SmallInteger, default=3)
    level = Column(String(8), default="medium")
    owner_user_id = Column(BigInteger, nullable=False)
    mitigation = Column(Text)
    trigger_condition = Column(Text)
    review_cycle_days = Column(BigInteger, default=14)
    next_review_at = Column(DateTime, nullable=False)
    status = Column(String(16), default="open")
    in_library = Column(Boolean, default=False)
    closed_at = Column(DateTime)


class Issue(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "issue"
    project_id = Column(BigInteger, nullable=False)
    code = Column(String(64), nullable=False, unique=True)
    title = Column(String(200), nullable=False)
    severity = Column(String(8), default="p2")
    owner_user_id = Column(BigInteger, nullable=False)
    status = Column(String(16), default="open")
    due_at = Column(DateTime)
    escalated_at = Column(DateTime)
    source = Column(String(32))


class ChangeRequest(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "change_request"
    project_id = Column(BigInteger, nullable=False)
    code = Column(String(64), nullable=False, unique=True)
    title = Column(String(200), nullable=False)
    change_type = Column(String(16), nullable=False)
    impact = Column(JSON)
    status = Column(String(16), default="draft")
    approved_by = Column(BigInteger)
    baseline_id = Column(BigInteger)
