import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from database import Base

class VerificationDeadJob(Base):
    __tablename__ = "verification_dead_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(nullable=False)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    failure_reason = Column(Text, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    payload_json = Column(Text, nullable=True)
    failed_at = Column(DateTime(timezone=True), server_default=func.now())
