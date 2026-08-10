import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from entities.otp import OTPVerification

class OTPRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, otp: OTPVerification) -> None:
        self.db.add(otp)
        self.db.commit()
        self.db.refresh(otp)

    def FindLatestActive(self, doctor_id: UUID, purpose: str) -> Optional[OTPVerification]:
        return self.db.query(OTPVerification).filter(
            OTPVerification.doctor_id == str(doctor_id),
            OTPVerification.purpose == purpose,
            OTPVerification.is_verified == False
        ).order_by(OTPVerification.created_at.desc()).first()

    def IncrementAttempt(self, otp_id: UUID) -> None:
        self.db.query(OTPVerification).filter(OTPVerification.id == str(otp_id)).update({
            "attempt_count": OTPVerification.attempt_count + 1
        })
        self.db.commit()

    def MarkVerified(self, otp_id: UUID) -> None:
        self.db.query(OTPVerification).filter(OTPVerification.id == str(otp_id)).update({"is_verified": True})
        self.db.commit()

    def InvalidatePreviousOTPs(self, doctor_id: UUID, purpose: str) -> None:
        now = datetime.datetime.now()
        self.db.query(OTPVerification).filter(
            OTPVerification.doctor_id == str(doctor_id),
            OTPVerification.purpose == purpose,
            OTPVerification.is_verified == False
        ).update({"expires_at": now})
        self.db.commit()
