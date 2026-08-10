import enum
import uuid
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class DocumentType(str, enum.Enum):
    REGISTRATION_CERTIFICATE = "REGISTRATION_CERTIFICATE"
    MBBS_CERTIFICATE = "MBBS_CERTIFICATE"
    MD_CERTIFICATE = "MD_CERTIFICATE"
    MEDICAL_DEGREE_CERTIFICATE = "MEDICAL_DEGREE_CERTIFICATE"
    PG_CERTIFICATE = "PG_CERTIFICATE"
    AADHAAR = "AADHAAR"
    PAN = "PAN"
    PASSPORT = "PASSPORT"

class OCRStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DoctorDocument(Base):
    __tablename__ = "doctor_documents"

    document_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(Enum(DocumentType, name="document_type_enum", native_enum=False), nullable=False, index=True)
    file_url = Column(Text, nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    resolution_width = Column(Integer, nullable=True)
    resolution_height = Column(Integer, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_latest = Column(Boolean, default=True, nullable=False)
    ocr_status = Column(Enum(OCRStatus, name="ocr_status_enum", native_enum=False), default=OCRStatus.PENDING, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), index=True, nullable=True)

    # Relations
    ocr_results = relationship("DocumentOCRResult", backref="document", cascade="all, delete")
