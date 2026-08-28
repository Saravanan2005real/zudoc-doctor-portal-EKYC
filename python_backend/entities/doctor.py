import enum
import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class DoctorStatus(str, enum.Enum):
    NOT_SUBMITTED = "NOT_SUBMITTED"
    PENDING = "PENDING"
    AUTO_VERIFIED = "AUTO_VERIFIED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    DOCUMENTS_REQUESTED = "DOCUMENTS_REQUESTED"

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    gender = Column(String(20), nullable=True)
    dob = Column(DateTime(timezone=True), nullable=True)
    mobile = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    profile_photo = Column(Text, nullable=True)
    languages = Column(String(255), nullable=True)
    biography = Column(Text, nullable=True)
    status = Column(Enum(DoctorStatus, name="doctor_status_enum", native_enum=False), default=DoctorStatus.NOT_SUBMITTED, nullable=False, index=True)
    fraud_score = Column(Integer, default=0)
    mobile_verified = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    account_locked_until = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    assigned_admin_id = Column(String(36), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    prescription_enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), index=True, nullable=True)
    deleted_by = Column(String(36), nullable=True)

    # Relationships
    licenses = relationship("DoctorLicense", backref="doctor", cascade="all, delete")
    qualifications = relationship("DoctorQualification", backref="doctor", cascade="all, delete")
    clinics = relationship("DoctorClinic", backref="doctor", cascade="all, delete")
    documents = relationship("DoctorDocument", backref="doctor", cascade="all, delete")
    histories = relationship("VerificationHistory", backref="doctor", cascade="all, delete")
    otps = relationship("OTPVerification", backref="doctor", cascade="all, delete")
    refresh_tokens = relationship("RefreshToken", backref="doctor", cascade="all, delete")
    notes = relationship("DoctorNote", backref="doctor", cascade="all, delete")
    flags = relationship("VerificationFlag", backref="doctor", cascade="all, delete")
    admin_actions = relationship("AdminAction", backref="doctor", cascade="all, delete")
