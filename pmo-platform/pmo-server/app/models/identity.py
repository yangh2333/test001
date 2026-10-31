"""组织与身份域模型（M10）。"""
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Text, JSON, ForeignKey
from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin, SoftDeleteMixin


class Dept(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "dept"
    name = Column(String(128), nullable=False)
    parent_id = Column(BigInteger, ForeignKey("dept.id"))
    source_id = Column(String(64), nullable=False)
    path = Column(String(512), nullable=False)
    manager_user_id = Column(BigInteger)
    order_no = Column(BigInteger, default=0)
    status = Column(String(16), default="active")


class User(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "user"
    employee_no = Column(String(32), nullable=False, unique=True)
    name = Column(String(64), nullable=False)
    email = Column(String(128), nullable=False)
    dept_id = Column(BigInteger, ForeignKey("dept.id"))
    title = Column(String(64))
    avatar_url = Column(String(512))
    status = Column(String(16), default="active")
    src_ldap = Column(Boolean, default=False)
    src_wechat = Column(Boolean, default=False)
    src_synced_at = Column(DateTime)
    password_hash = Column(String(255))
    is_external = Column(Boolean, default=False)
    last_login_at = Column(DateTime)


class ExternalAccount(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "external_account"
    login_name = Column(String(64), nullable=False, unique=True)
    display_name = Column(String(64), nullable=False)
    acct_type = Column(String(32), nullable=False)
    org_name = Column(String(128), nullable=False)
    project_ids = Column(JSON, default=list)
    field_whitelist = Column(JSON, default=dict)
    status = Column(String(16), default="invited")
    mfa_secret = Column(String(128))
    expires_at = Column(DateTime, nullable=False)
    last_login_at = Column(DateTime)
    password_hash = Column(String(255), nullable=False)


class SyncConflict(IdMixin, TimestampMixin, Base):
    __tablename__ = "sync_conflict"
    employee_no = Column(String(32), nullable=False)
    conflict_type = Column(String(32), nullable=False)
    ldap_payload = Column(JSON)
    wechat_payload = Column(JSON)
    status = Column(String(16), default="pending")
    resolved_by = Column(BigInteger)
    resolution = Column(String(32))
    resolved_at = Column(DateTime)


class Role(IdMixin, TimestampMixin, Base):
    __tablename__ = "role"
    code = Column(String(32), nullable=False, unique=True)
    name = Column(String(64), nullable=False)
    scope = Column(String(16), default="global")
    builtin = Column(Boolean, default=True)


class RoleBinding(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "role_binding"
    user_id = Column(BigInteger, nullable=False)
    role_id = Column(BigInteger, ForeignKey("role.id"), nullable=False)
    project_id = Column(BigInteger)
    dept_id = Column(BigInteger)
    granted_by = Column(BigInteger, nullable=False)
    expires_at = Column(DateTime)


class DataDomain(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "data_domain"
    code = Column(String(32), nullable=False, unique=True)
    name = Column(String(64), nullable=False)
    expr = Column(JSON, nullable=False)
    description = Column(Text)
