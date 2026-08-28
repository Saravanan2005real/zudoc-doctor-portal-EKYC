import enum
import uuid
from sqlalchemy import Column, String, DateTime, Float, Enum, ForeignKey, Text, Numeric
from sqlalchemy.sql import func
from database import Base

class ConsultationMode(str, enum.Enum):
    IN_PERSON = "IN_PERSON"
    OFFLINE = "IN_PERSON"
    VIDEO = "VIDEO"
    BOTH = "BOTH"

class DoctorClinic(Base):
    __tablename__ = "doctor_clinics"

    clinic_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    clinic_name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False)
    pincode = Column(String(20), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    consultation_mode = Column(Enum(ConsultationMode, name="consultation_mode_enum", native_enum=False), default=ConsultationMode.IN_PERSON, nullable=False)
    consultation_fee = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), index=True, nullable=True)
