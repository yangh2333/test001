"""项目与门禁域模型（M1 + M4）。"""
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Date, Text, JSON,
    ForeignKey, Numeric,
)
from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin, SoftDeleteMixin


class Program(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "program"
    code = Column(String(64), nullable=False, unique=True)
    name = Column(String(128), nullable=False)
    owner_user_id = Column(BigInteger, nullable=False)
    secrecy_level = Column(String(16), default="internal")
    target_date = Column(Date)
    status = Column(String(16), default="active")
    description = Column(Text)
    created_by = Column(BigInteger)


class ProjectType(IdMixin, TimestampMixin, Base):
    __tablename__ = "project_type"
    code = Column(String(32), nullable=False, unique=True)
    name = Column(String(64), nullable=False)
    sort_order = Column(BigInteger, default=0)
    enabled = Column(Boolean, default=True)


class Project(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "project"
    code = Column(String(64), nullable=False)
    name = Column(String(200), nullable=False)
    program_id = Column(BigInteger, ForeignKey("program.id"))
    type_id = Column(BigInteger, ForeignKey("project_type.id"), nullable=False)
    pm_user_id = Column(BigInteger, nullable=False)
    dept_id = Column(BigInteger, ForeignKey("dept.id"), nullable=False)
    status = Column(String(16), default="draft")
    secrecy_level = Column(String(16), nullable=False)
    current_stage_id = Column(BigInteger)
    progress_pct = Column(Numeric(5, 2), default=0)
    health = Column(String(8), default="na")
    health_updated_at = Column(DateTime)
    plan_start = Column(Date, nullable=False)
    plan_end = Column(Date, nullable=False)
    actual_start = Column(Date)
    actual_end = Column(Date)
    baseline_id = Column(BigInteger)
    data_pedigree = Column(String(16), default="trial")
    milestone_summary = Column(JSON)
    created_by = Column(BigInteger)


class ProjectStakeholder(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "project_stakeholder"
    project_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    role_label = Column(String(32), nullable=False)


class StageTemplate(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "stage_template"
    type_id = Column(BigInteger, ForeignKey("project_type.id"), nullable=False)
    code = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    order_no = Column(BigInteger, nullable=False)
    is_core = Column(Boolean, default=False)
    typical_days = Column(BigInteger)


class ChecklistTemplate(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "checklist_template"
    code = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    version = Column(BigInteger, default=1)
    items = Column(JSON, default=list)
    status = Column(String(16), default="draft")


class GateTemplate(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "gate_template"
    type_id = Column(BigInteger, ForeignKey("project_type.id"), nullable=False)
    stage_template_id = Column(BigInteger, ForeignKey("stage_template.id"))
    code = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    order_no = Column(BigInteger, nullable=False)
    is_core = Column(Boolean, default=False)
    is_high_risk = Column(Boolean, default=False)
    signoff_roles = Column(JSON)
    checklist_template_id = Column(BigInteger, ForeignKey("checklist_template.id"))
    enforce_mode = Column(String(16), default="commitment")


class ProjectStage(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "project_stage"
    project_id = Column(BigInteger, nullable=False)
    template_id = Column(BigInteger, ForeignKey("stage_template.id"))
    name = Column(String(128), nullable=False)
    order_no = Column(BigInteger, nullable=False)
    status = Column(String(16), default="not_started")
    plan_start = Column(Date)
    plan_end = Column(Date)
    actual_start = Column(Date)
    actual_end = Column(Date)
    is_tailored = Column(Boolean, default=False)
    tailor_reason = Column(Text)


class Gate(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "gate"
    project_id = Column(BigInteger, nullable=False)
    stage_id = Column(BigInteger, ForeignKey("project_stage.id"))
    template_id = Column(BigInteger, ForeignKey("gate_template.id"))
    name = Column(String(128), nullable=False)
    status = Column(String(16), default="not_started")
    decision = Column(String(16))
    decided_by = Column(BigInteger)
    decided_at = Column(DateTime)
    is_high_risk = Column(Boolean, default=False)
    enforce_mode = Column(String(16), default="commitment")
    gap_items = Column(JSON)
    waive_reason = Column(Text)
    blocked_flag = Column(Boolean, default=False)


class ChecklistInstance(IdMixin, TimestampMixin, Base):
    __tablename__ = "checklist_instance"
    gate_id = Column(BigInteger, nullable=False)
    template_id = Column(BigInteger, ForeignKey("checklist_template.id"))
    template_version = Column(BigInteger, default=1)
    items = Column(JSON, default=list)
    total_count = Column(BigInteger, default=0)
    done_count = Column(BigInteger, default=0)


class Review(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "review"
    gate_id = Column(BigInteger, nullable=False)
    title = Column(String(200), nullable=False)
    scheduled_at = Column(DateTime)
    status = Column(String(16), default="draft")
    conclusion = Column(Text)
    minutes_url = Column(String(512))
    created_by = Column(BigInteger)


class ReviewItem(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "review_item"
    review_id = Column(BigInteger, nullable=False)
    kind = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    owner_user_id = Column(BigInteger, nullable=False)
    due_date = Column(Date)
    status = Column(String(16), default="open")
    todo_id = Column(BigInteger)
    closed_at = Column(DateTime)


class ReviewSignoff(IdMixin, TimestampMixin, Base):
    __tablename__ = "review_signoff"
    review_id = Column(BigInteger, nullable=False)
    role_code = Column(String(32), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    status = Column(String(16), default="pending")
    delegated_from = Column(BigInteger)
    signed_at = Column(DateTime)
    comment = Column(Text)
