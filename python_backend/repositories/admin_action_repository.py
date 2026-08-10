from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from entities.admin_action import AdminAction

class AdminActionRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, action: AdminAction) -> None:
        self.db.add(action)
        self.db.commit()
        self.db.refresh(action)

    def FindByDoctorID(self, doctor_id: UUID) -> List[AdminAction]:
        return self.db.query(AdminAction).filter(AdminAction.doctor_id == doctor_id).order_by(AdminAction.created_at.desc()).all()
