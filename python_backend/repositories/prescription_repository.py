from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from entities.prescription import Prescription

class PrescriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, p: Prescription) -> None:
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)

    def FindByDoctorID(self, doctor_id: UUID) -> List[Prescription]:
        return self.db.query(Prescription).filter(Prescription.doctor_id == doctor_id).order_by(Prescription.issued_at.desc()).all()

    def FindByID(self, id: UUID) -> Optional[Prescription]:
        return self.db.query(Prescription).filter(Prescription.prescription_id == id).first()
