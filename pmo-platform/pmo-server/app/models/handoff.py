"""交接物模型（M2）。"""
from sqlalchemy import Column, BigInteger, String, DateTime, Date, Text, ForeignKey
from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin, SoftDeleteMixin


class Deliverable(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "deliverable"
    project_id = Column(BigInteger, nullable=False)
    name = Column(String(200), nullable=False)
    deliver_type = Column(String(32), nullable=False)
    from_project_id = Column(BigInteger)
    to_project_id = Column(BigInteger)
    from_user_id = Column(BigInteger, nullable=False)
    to_user_id = Column(BigInteger, nullable=False)
    due_date = Column(Date, nullable=False)
    file_url = Column(String(512))
    status = Column(String(16), default="pending")
    delivered_at = Column(DateTime)
    accepted_at = Column(DateTime)
