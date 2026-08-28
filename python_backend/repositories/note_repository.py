from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from entities.note import DoctorNote

class NoteRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, note: DoctorNote) -> None:
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)

    def FindByDoctorID(self, doctor_id: UUID) -> List[DoctorNote]:
        return self.db.query(DoctorNote).filter(DoctorNote.doctor_id == doctor_id).order_by(DoctorNote.created_at.desc()).all()
