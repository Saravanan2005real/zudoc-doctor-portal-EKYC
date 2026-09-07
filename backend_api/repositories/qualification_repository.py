from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from entities.qualification import DoctorQualification

class QualificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, qual: DoctorQualification) -> None:
        self.db.add(qual)
        self.db.commit()
        self.db.refresh(qual)

    def FindByDoctorID(self, doctor_id: UUID) -> List[DoctorQualification]:
        return self.db.query(DoctorQualification).filter(
            DoctorQualification.doctor_id == str(doctor_id)
        ).all()

    def Delete(self, qualification_id: UUID, doctor_id: UUID) -> None:
        self.db.query(DoctorQualification).filter(
            DoctorQualification.qualification_id == str(qualification_id),
            DoctorQualification.doctor_id == str(doctor_id),
        ).delete()
        self.db.commit()
