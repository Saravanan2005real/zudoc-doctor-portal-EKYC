from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from entities.ocr_result import DocumentOCRResult

class OCRRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, ocr_result: DocumentOCRResult) -> None:
        self.db.add(ocr_result)
        self.db.commit()
        self.db.refresh(ocr_result)

    def FindByDocumentID(self, document_id: UUID) -> List[DocumentOCRResult]:
        return self.db.query(DocumentOCRResult).filter(DocumentOCRResult.document_id == document_id).order_by(DocumentOCRResult.processed_at.desc()).all()

    def FindLatestByDocumentID(self, document_id: UUID) -> Optional[DocumentOCRResult]:
        return self.db.query(DocumentOCRResult).filter(DocumentOCRResult.document_id == document_id).order_by(DocumentOCRResult.processed_at.desc()).first()
