import enum
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from database import Base

class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class DoctorLicense(Base):
    __tablename__ = "doctor_licenses"

    license_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    registration_number = Column(String(100), nullable=False, index=True)
    registration_council = Column(String(255), nullable=False)
    registration_year = Column(Integer, nullable=False)
    issue_date = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    license_status = Column(String(50), default='ACTIVE')
    verification_status = Column(Enum(VerificationStatus, name="verification_status_enum", native_enum=False), default=VerificationStatus.UNVERIFIED, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), index=True, nullable=True)
