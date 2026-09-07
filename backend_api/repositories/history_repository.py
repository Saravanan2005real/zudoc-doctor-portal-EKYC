from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from entities.history import VerificationHistory

class VerificationHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, history: VerificationHistory) -> None:
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)

    def FindByDoctorID(self, doctor_id: UUID) -> List[VerificationHistory]:
        return self.db.query(VerificationHistory).filter(
            VerificationHistory.doctor_id == str(doctor_id)
        ).order_by(VerificationHistory.performed_at.desc()).all()
