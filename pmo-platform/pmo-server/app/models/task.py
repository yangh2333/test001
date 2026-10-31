"""任务与进度域模型（M1）。"""
from datetime import datetime
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Date, Text, JSON,
    ForeignKey, Numeric, SmallInteger,
)
from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin, SoftDeleteMixin


class Wbs(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "wbs"
    project_id = Column(BigInteger, nullable=False)
    parent_id = Column(BigInteger, ForeignKey("wbs.id"))
    code = Column(String(64), nullable=False)
    name = Column(String(200), nullable=False)
    level = Column(SmallInteger, nullable=False)
    order_no = Column(BigInteger, default=0)


class Task(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "task"
    project_id = Column(BigInteger, nullable=False)
    wbs_id = Column(BigInteger, ForeignKey("wbs.id"))
    parent_id = Column(BigInteger, ForeignKey("task.id"))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    owner_user_id = Column(BigInteger, nullable=False)
    assignee_ids = Column(JSON)
    consult_ids = Column(JSON)
    inform_ids = Column(JSON)
    plan_start = Column(Date, nullable=False)
    plan_end = Column(Date, nullable=False)
    actual_start = Column(Date)
    actual_end = Column(Date)
    est_hours = Column(Numeric(8, 2))
    progress_pct = Column(Numeric(5, 2), default=0)
    status = Column(String(16), default="not_started")
    blocked_reason = Column(Text)
    blocked_help_user_id = Column(BigInteger)
    priority = Column(SmallInteger, default=3)
    is_milestone = Column(Boolean, default=False)
    is_critical = Column(Boolean, default=False)
    ci_status = Column(String(16))
    ci_ref = Column(String(128))
    baseline_offset_days = Column(BigInteger)
    external_ref = Column(String(128))
    created_by = Column(BigInteger)


class TaskRaci(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "task_raci"
    task_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    raci = Column(String(1), nullable=False)
    is_primary_accountable = Column(Boolean, default=False)


class Dependency(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "dependency"
    predecessor_task_id = Column(BigInteger, nullable=False)
    successor_task_id = Column(BigInteger, nullable=False)
    dep_type = Column(String(2), default="FS")
    lag_days = Column(BigInteger, default=0)
    cross_project = Column(Boolean, default=False)


class Baseline(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "baseline"
    project_id = Column(BigInteger, nullable=False)
    name = Column(String(100), nullable=False)
    kind = Column(String(16), nullable=False)
    snapshot_at = Column(DateTime, nullable=False)
    created_by = Column(BigInteger)


class BaselineTask(IdMixin, Base):
    __tablename__ = "baseline_task"
    baseline_id = Column(BigInteger, nullable=False)
    task_id = Column(BigInteger, nullable=False)
    plan_start = Column(Date, nullable=False)
    plan_end = Column(Date, nullable=False)
    est_hours = Column(Numeric(8, 2))
    progress_pct = Column(Numeric(5, 2))
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class Milestone(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "milestone"
    project_id = Column(BigInteger, nullable=False)
    task_id = Column(BigInteger)
    name = Column(String(200), nullable=False)
    kind = Column(String(32))
    plan_date = Column(Date, nullable=False)
    actual_date = Column(Date)
    status = Column(String(16), default="pending")
    is_critical = Column(Boolean, default=False)
