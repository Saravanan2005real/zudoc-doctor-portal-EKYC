import enum
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum, ForeignKey
from sqlalchemy.sql import func
from database import Base

class FlagSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class VerificationFlag(Base):
    __tablename__ = "verification_flags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    flag_type = Column(String(100), nullable=False)
    severity = Column(Enum(FlagSeverity, name="flag_severity_enum", native_enum=False), default=FlagSeverity.MEDIUM, nullable=False)
    message = Column(Text, nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)
    resolved_by = Column(String(36), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
