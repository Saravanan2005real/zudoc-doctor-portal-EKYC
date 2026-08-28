import uuid
from sqlalchemy import Column, String, Integer, BigInteger, Float, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from database import Base

class DocumentOCRResult(Base):
    __tablename__ = "document_ocr_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("doctor_documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    raw_json = Column(Text, nullable=False)
    parsed_json = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    processing_time_ms = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
