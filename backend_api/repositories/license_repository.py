from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from entities.license import DoctorLicense

class LicenseRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, license: DoctorLicense) -> None:
        self.db.add(license)
        self.db.commit()
        self.db.refresh(license)

    def FindByDoctorID(self, doctor_id: UUID) -> List[DoctorLicense]:
        return self.db.query(DoctorLicense).filter(DoctorLicense.doctor_id == str(doctor_id)).all()

    def Delete(self, license_id: UUID, doctor_id: UUID) -> None:
        self.db.query(DoctorLicense).filter(
            DoctorLicense.license_id == str(license_id),
            DoctorLicense.doctor_id == str(doctor_id),
        ).delete()
        self.db.commit()
