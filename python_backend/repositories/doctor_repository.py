import datetime
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_
from entities.doctor import Doctor

class DoctorRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, doctor: Doctor) -> None:
        self.db.add(doctor)
        self.db.commit()
        self.db.refresh(doctor)

    def FindByEmail(self, email: str) -> Optional[Doctor]:
        return self.db.query(Doctor).filter(Doctor.email == email).first()

    def FindByMobile(self, mobile: str) -> Optional[Doctor]:
        return self.db.query(Doctor).filter(Doctor.mobile == mobile).first()

    def FindByIdentifier(self, identifier: str) -> Optional[Doctor]:
        return self.db.query(Doctor).filter(or_(Doctor.email == identifier, Doctor.mobile == identifier)).first()

    def FindByPublicID(self, public_id: UUID) -> Optional[Doctor]:
        return self.db.query(Doctor).filter(Doctor.public_id == str(public_id)).first()

    def Update(self, doctor: Doctor) -> None:
        self.db.merge(doctor)
        self.db.commit()

    def IncrementFailedLogin(self, doctor_id: UUID, max_attempts: int, lock_duration: datetime.timedelta) -> Tuple[int, bool]:
        doc = self.db.query(Doctor).filter(Doctor.id == str(doctor_id)).first()
        if not doc:
            raise Exception("Doctor not found")
        
        doc.failed_login_attempts += 1
        is_locked = False
        if doc.failed_login_attempts >= max_attempts:
            locked_until = datetime.datetime.now() + lock_duration
            doc.account_locked_until = locked_until
            is_locked = True
            
        self.db.commit()
        self.db.refresh(doc)
        return doc.failed_login_attempts, is_locked

    def ResetFailedLogin(self, doctor_id: UUID) -> None:
        now = datetime.datetime.now()
        self.db.query(Doctor).filter(Doctor.id == str(doctor_id)).update({
            "failed_login_attempts": 0,
            "account_locked_until": None,
            "last_login_at": now
        })
        self.db.commit()

    def MarkMobileVerified(self, doctor_id: UUID) -> None:
        self.db.query(Doctor).filter(Doctor.id == str(doctor_id)).update({"mobile_verified": True})
        self.db.commit()
