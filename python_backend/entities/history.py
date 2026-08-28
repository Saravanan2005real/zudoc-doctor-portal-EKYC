import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from database import Base

class VerificationHistory(Base):
    __tablename__ = "verification_histories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    remarks = Column(Text, nullable=True)
    performed_by = Column(String(36), nullable=True)
    performed_at = Column(DateTime(timezone=True), server_default=func.now())
