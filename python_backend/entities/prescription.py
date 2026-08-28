import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Prescription(Base):
    __tablename__ = "prescriptions"

    prescription_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(String(100), nullable=False)
    diagnosis = Column(Text, nullable=False)
    medicines_json = Column(Text, nullable=False)
    digital_signature = Column(Text, nullable=False)
    qr_payload = Column(Text, nullable=False)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
