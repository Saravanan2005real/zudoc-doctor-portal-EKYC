import uuid
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class AuditEvent(Base):
    __tablename__ = "audit_events"

    event_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_type = Column(String(50), nullable=False, index=True)
    actor_id = Column(String(36), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=False)
    before_state = Column(Text, nullable=True)
    after_state = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    device = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
