"""平台底座模型（M10）。"""
from datetime import datetime
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Text, JSON,
    ForeignKey, Numeric,
)
from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin, SoftDeleteMixin


class Attachment(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "attachment"
    object_type = Column(String(32), nullable=False)
    object_id = Column(BigInteger, nullable=False)
    file_name = Column(String(255), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    storage_key = Column(String(512), nullable=False)
    uploaded_by = Column(BigInteger, nullable=False)


class AuditLog(IdMixin, Base):
    __tablename__ = "audit_log"
    actor_user_id = Column(BigInteger)
    actor_type = Column(String(16), default="internal")
    action = Column(String(64), nullable=False)
    object_type = Column(String(32), nullable=False)
    object_id = Column(BigInteger)
    before = Column(JSON)
    after = Column(JSON)
    ip = Column(String(64))
    user_agent = Column(String(512))
    trace_id = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class ImportJob(IdMixin, TimestampMixin, Base):
    __tablename__ = "import_job"
    import_type = Column(String(32), nullable=False)
    file_url = Column(String(512), nullable=False)
    mapping = Column(JSON, default=dict)
    status = Column(String(16), default="uploaded")
    total_rows = Column(BigInteger, default=0)
    success_rows = Column(BigInteger, default=0)
    failed_rows = Column(BigInteger, default=0)
    error_report_url = Column(String(512))
    operator_id = Column(BigInteger, nullable=False)
    rollback_token = Column(String(64), nullable=False)


class Dictionary(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "dictionary"
    category = Column(String(32), nullable=False)
    code = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    sort_order = Column(BigInteger, default=0)
    status = Column(String(16), default="active")


class Template(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "template"
    tpl_type = Column(String(16), nullable=False)
    code = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    version = Column(BigInteger, default=1)
    content = Column(JSON, default=dict)
    status = Column(String(16), default="draft")
    tailorable = Column(Boolean, default=True)


class SecrecyChangeRequest(IdMixin, TimestampMixin, Base):
    __tablename__ = "secrecy_change_request"
    project_id = Column(BigInteger, nullable=False)
    from_level = Column(String(16), nullable=False)
    to_level = Column(String(16), nullable=False)
    reason = Column(Text, nullable=False)
    requested_by = Column(BigInteger, nullable=False)
    approver1_id = Column(BigInteger)
    approver2_id = Column(BigInteger)
    status = Column(String(16), default="pending")


class IntegrationConfig(IdMixin, TimestampMixin, Base):
    __tablename__ = "integration_config"
    code = Column(String(32), nullable=False, unique=True)
    name = Column(String(64), nullable=False)
    enabled = Column(Boolean, default=False)
    params = Column(Text)  # 简化：JSON 字符串，生产应加密
    last_sync_at = Column(DateTime)
    last_status = Column(String(16))
    fail_count = Column(BigInteger, default=0)


class AiCallLog(IdMixin, Base):
    __tablename__ = "ai_call_log"
    user_id = Column(BigInteger, nullable=False)
    scene = Column(String(32), nullable=False)
    provider = Column(String(32), nullable=False)
    token_in = Column(BigInteger, default=0)
    token_out = Column(BigInteger, default=0)
    cost_cent = Column(Numeric(10, 4), default=0)
    latency_ms = Column(BigInteger, default=0)
    status = Column(String(16), nullable=False)
    request_digest = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
