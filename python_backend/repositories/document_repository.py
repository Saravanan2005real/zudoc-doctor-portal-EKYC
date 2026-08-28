from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from entities.document import DoctorDocument


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, doc: DoctorDocument) -> None:
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

    def FindByDoctorID(self, doctor_id: UUID) -> List[DoctorDocument]:
        return self.db.query(DoctorDocument).filter(
            DoctorDocument.doctor_id == str(doctor_id),
            DoctorDocument.is_latest == True,
        ).all()

    def FindByDoctorAndType(self, doctor_id: UUID, doc_type: str) -> List[DoctorDocument]:
        return self.db.query(DoctorDocument).filter(
            DoctorDocument.doctor_id == str(doctor_id),
            DoctorDocument.document_type == doc_type,
        ).order_by(DoctorDocument.version.desc()).all()

    def FindLatestByDoctorAndType(self, doctor_id: UUID, doc_type: str) -> Optional[DoctorDocument]:
        return self.db.query(DoctorDocument).filter(
            DoctorDocument.doctor_id == str(doctor_id),
            DoctorDocument.document_type == doc_type,
            DoctorDocument.is_latest == True,
        ).first()

    def FindByHash(self, doctor_id: UUID, file_hash: str) -> Optional[DoctorDocument]:
        return self.db.query(DoctorDocument).filter(
            DoctorDocument.doctor_id == str(doctor_id),
            DoctorDocument.file_hash == file_hash,
            DoctorDocument.is_latest == True,
        ).first()

    def MarkPreviousVersionsNotLatest(self, doctor_id: UUID, doc_type: str) -> None:
        self.db.query(DoctorDocument).filter(
            DoctorDocument.doctor_id == str(doctor_id),
            DoctorDocument.document_type == doc_type,
            DoctorDocument.is_latest == True,
        ).update({"is_latest": False})
        self.db.commit()

    def Delete(self, document_id: UUID, doctor_id: UUID) -> None:
        self.db.query(DoctorDocument).filter(
            DoctorDocument.document_id == str(document_id),
            DoctorDocument.doctor_id == str(doctor_id),
        ).delete()
        self.db.commit()
