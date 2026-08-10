from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from entities.clinic import DoctorClinic

class ClinicRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, clinic: DoctorClinic) -> None:
        self.db.add(clinic)
        self.db.commit()
        self.db.refresh(clinic)

    def FindByDoctorID(self, doctor_id: UUID) -> List[DoctorClinic]:
        return self.db.query(DoctorClinic).filter(DoctorClinic.doctor_id == str(doctor_id)).all()

    def Delete(self, clinic_id: UUID, doctor_id: UUID) -> None:
        self.db.query(DoctorClinic).filter(
            DoctorClinic.clinic_id == str(clinic_id),
            DoctorClinic.doctor_id == str(doctor_id),
        ).delete()
        self.db.commit()
