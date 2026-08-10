import enum
import uuid
from sqlalchemy import Column, String, DateTime, Text, Enum, ForeignKey
from sqlalchemy.sql import func
from database import Base

class NoteVisibility(str, enum.Enum):
    INTERNAL = "INTERNAL"
    VISIBLE_TO_DOCTOR = "VISIBLE_TO_DOCTOR"

class DoctorNote(Base):
    __tablename__ = "doctor_notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id = Column(String(36), nullable=False, index=True)
    note = Column(Text, nullable=False)
    visibility = Column(Enum(NoteVisibility, name="note_visibility_enum", native_enum=False), default=NoteVisibility.INTERNAL, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
