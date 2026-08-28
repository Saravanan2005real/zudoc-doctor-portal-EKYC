import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from entities.job import VerificationJob

class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, job: VerificationJob) -> None:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

    def FetchNextQueuedJob(self) -> Optional[VerificationJob]:
        # Assuming entities.JobStatusQueued or 'QUEUED' string is used, adjust as necessary
        return self.db.query(VerificationJob).filter(
            VerificationJob.status == "QUEUED"  # Replace with appropriate constant if available
        ).order_by(VerificationJob.priority.desc(), VerificationJob.created_at.asc()).first()

    def UpdateStatus(self, job_id: UUID, status: str, last_error: Optional[str] = None) -> None:
        updates = {"status": status}
        if last_error is not None:
            updates["last_error"] = last_error
        self.db.query(VerificationJob).filter(VerificationJob.job_id == job_id).update(updates)
        self.db.commit()

    def MarkRunning(self, job_id: UUID) -> None:
        now = datetime.datetime.now()
        self.db.query(VerificationJob).filter(VerificationJob.job_id == job_id).update({
            "status": "RUNNING",
            "started_at": now
        })
        self.db.commit()

    def MarkCompleted(self, job_id: UUID) -> None:
        now = datetime.datetime.now()
        self.db.query(VerificationJob).filter(VerificationJob.job_id == job_id).update({
            "status": "SUCCESS",
            "completed_at": now
        })
        self.db.commit()

    def MarkFailed(self, job_id: UUID, err_str: str) -> None:
        now = datetime.datetime.now()
        self.db.query(VerificationJob).filter(VerificationJob.job_id == job_id).update({
            "status": "FAILED",
            "last_error": err_str,
            "completed_at": now
        })
        self.db.commit()

    def FindByDoctorID(self, doctor_id: UUID) -> List[VerificationJob]:
        return self.db.query(VerificationJob).filter(VerificationJob.doctor_id == doctor_id).order_by(VerificationJob.created_at.desc()).all()

    def FindByID(self, job_id: UUID) -> Optional[VerificationJob]:
        return self.db.query(VerificationJob).filter(VerificationJob.job_id == job_id).first()
