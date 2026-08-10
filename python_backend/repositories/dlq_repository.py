from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from entities.dlq import VerificationDeadJob

class DLQRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, dead_job: VerificationDeadJob) -> None:
        self.db.add(dead_job)
        self.db.commit()
        self.db.refresh(dead_job)

    def FindAll(self) -> List[VerificationDeadJob]:
        return self.db.query(VerificationDeadJob).order_by(VerificationDeadJob.failed_at.desc()).all()

    def FindByID(self, id: UUID) -> Optional[VerificationDeadJob]:
        return self.db.query(VerificationDeadJob).filter(VerificationDeadJob.id == id).first()

    def Delete(self, id: UUID) -> None:
        self.db.query(VerificationDeadJob).filter(VerificationDeadJob.id == id).delete()
        self.db.commit()
