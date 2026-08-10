import datetime
from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from entities.flag import VerificationFlag

class FlagRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, flag: VerificationFlag) -> None:
        self.db.add(flag)
        self.db.commit()
        self.db.refresh(flag)

    def FindByDoctorID(self, doctor_id: UUID) -> List[VerificationFlag]:
        return self.db.query(VerificationFlag).filter(VerificationFlag.doctor_id == doctor_id).order_by(VerificationFlag.created_at.desc()).all()

    def ResolveFlag(self, flag_id: UUID, admin_id: UUID) -> None:
        now = datetime.datetime.now()
        self.db.query(VerificationFlag).filter(VerificationFlag.id == flag_id).update({
            "resolved": True,
            "resolved_by": admin_id,
            "resolved_at": now
        })
        self.db.commit()
