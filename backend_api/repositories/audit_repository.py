from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from entities.audit import AuditEvent

class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, event: AuditEvent) -> None:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

    def FindByActorID(self, actor_id: UUID) -> List[AuditEvent]:
        return self.db.query(AuditEvent).filter(AuditEvent.actor_id == actor_id).order_by(AuditEvent.timestamp.desc()).all()
