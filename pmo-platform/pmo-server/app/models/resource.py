"""资源与成本域模型（M3/M7，P1 建表）。"""
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Date, Text, JSON,
    ForeignKey, Numeric, SmallInteger,
)
from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin, SoftDeleteMixin


class Skill(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "skill"
    code = Column(String(64), nullable=False, unique=True)
    name = Column(String(128), nullable=False)
    category = Column(String(32), nullable=False)
    status = Column(String(16), default="active")
    merged_to = Column(BigInteger, ForeignKey("skill.id"))


class MemberSkill(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "member_skill"
    user_id = Column(BigInteger, nullable=False)
    skill_id = Column(BigInteger, ForeignKey("skill.id"), nullable=False)
    level = Column(SmallInteger, default=3)
    source = Column(String(16), default="self")
    verified_by = Column(BigInteger)


class ResourcePool(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "resource_pool"
    res_type = Column(String(16), nullable=False)
    name = Column(String(128), nullable=False)
    dept_id = Column(BigInteger, ForeignKey("dept.id"))
    owner_user_id = Column(BigInteger)
    capacity_unit = Column(String(16))
    status = Column(String(16), default="active")


class Reservation(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "reservation"
    project_id = Column(BigInteger, nullable=False)
    res_type = Column(String(16), nullable=False)
    resource_id = Column(BigInteger, nullable=False)
    percent = Column(Numeric(5, 2), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(16), default="requested")
    approved_by = Column(BigInteger)


class LabResource(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "lab_resource"
    name = Column(String(128), nullable=False)
    location = Column(String(128))
    env_spec = Column(Text)
    access_level = Column(String(16), default="normal")
    status = Column(String(16), default="available")


class LabBooking(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "lab_booking"
    lab_resource_id = Column(BigInteger, ForeignKey("lab_resource.id"), nullable=False)
    project_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    status = Column(String(16), default="booked")
    purpose = Column(Text)


class Batch(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "batch"
    project_id = Column(BigInteger, nullable=False)
    batch_type = Column(String(16), nullable=False)
    vendor_name = Column(String(128), nullable=False)
    lot_no = Column(String(64))
    status = Column(String(16), default="planned")
    plan_release_date = Column(Date)
    actual_release_date = Column(Date)
    plan_out_date = Column(Date)
    actual_out_date = Column(Date)
    qty = Column(BigInteger)
    shared_batch_id = Column(BigInteger, ForeignKey("batch.id"))
    source = Column(String(16), default="manual")


class BatchMilestone(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "batch_milestone"
    batch_id = Column(BigInteger, nullable=False)
    name = Column(String(64), nullable=False)
    plan_date = Column(Date)
    actual_date = Column(Date)
    status = Column(String(16), default="pending")
    source = Column(String(16), default="manual")


class CostShare(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "cost_share"
    batch_id = Column(BigInteger, nullable=False)
    project_id = Column(BigInteger, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    share_rule = Column(String(32), nullable=False)
    confirmed = Column(Boolean, default=False)


class Budget(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "budget"
    project_id = Column(BigInteger, nullable=False)
    category = Column(String(16), nullable=False)
    year_month = Column(String(7), nullable=False)
    planned_amount = Column(Numeric(14, 2), default=0)
    note = Column(Text)


class CostLedger(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "cost_ledger"
    project_id = Column(BigInteger, nullable=False)
    year_month = Column(String(7), nullable=False)
    category = Column(String(16), nullable=False)
    amount = Column(Numeric(14, 2), default=0)
    source = Column(String(16), default="manual")
    import_job_id = Column(BigInteger)


class Timesheet(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "timesheet"
    project_id = Column(BigInteger, nullable=False)
    task_id = Column(BigInteger)
    user_id = Column(BigInteger, nullable=False)
    week_start = Column(Date, nullable=False)
    hours = Column(Numeric(6, 2), nullable=False)
    note = Column(Text)
    status = Column(String(16), default="draft")
    approver_id = Column(BigInteger)
