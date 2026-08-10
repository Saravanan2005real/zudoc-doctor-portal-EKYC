import enum
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text, Enum, ForeignKey
from sqlalchemy.sql import func
from database import Base

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    RUNNING = "PROCESSING"
    COMPLETED = "COMPLETED"
    SUCCESS = "COMPLETED"
    FAILED = "FAILED"

class JobType(str, enum.Enum):
    FULL_PIPELINE = "FULL_PIPELINE"
    OCR_ONLY = "OCR_ONLY"
    OCR = "OCR_ONLY"
    COUNCIL_ONLY = "COUNCIL_ONLY"

class VerificationJob(Base):
    __tablename__ = "verification_jobs"

    job_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = Column(Enum(JobType, name="job_type_enum", native_enum=False), default=JobType.FULL_PIPELINE, nullable=False)
    status = Column(Enum(JobStatus, name="job_status_enum", native_enum=False), default=JobStatus.QUEUED, nullable=False, index=True)
    priority = Column(Integer, default=1, nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
