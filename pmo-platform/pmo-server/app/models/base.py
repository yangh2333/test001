"""模型基类与软删除混入。"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, func
from app.core.db import Base


class TimestampMixin:
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class SoftDeleteMixin:
    deleted_at = Column(DateTime, nullable=True)


class IdMixin:
    # SQLite 要求 INTEGER PRIMARY KEY 才能自增；其他数据库 Integer 也够用
    id = Column(Integer, primary_key=True, autoincrement=True)
