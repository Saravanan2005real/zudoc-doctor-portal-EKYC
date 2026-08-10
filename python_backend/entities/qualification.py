import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class DoctorQualification(Base):
    __tablename__ = "doctor_qualifications"

    qualification_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    degree = Column(String(100), nullable=False)
    specialization = Column(String(255), nullable=True)
    college = Column(String(255), nullable=False)
    university = Column(String(255), nullable=False)
    year_completed = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), index=True, nullable=True)
