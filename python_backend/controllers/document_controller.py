from fastapi import APIRouter, Header, Query, status, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from dependencies import get_db, get_document_service
from dto.profile_dto import DocumentUploadResponse

router = APIRouter(prefix="/api/v1/doctors", tags=["documents"])


def _error(status_code: int, message: str):
    return JSONResponse(status_code=status_code, content={"error": message})


def _serialize_doc(resp) -> dict:
    return {
        "document_id": str(resp.document_id),
        "doctor_id": str(resp.doctor_id),
        "document_type": resp.document_type,
        "file_url": resp.file_url,
        "original_filename": resp.original_filename,
        "mime_type": resp.mime_type,
        "file_size": resp.file_size,
        "file_hash": resp.file_hash,
        "version": resp.version,
        "is_latest": resp.is_latest,
        "ocr_status": resp.ocr_status,
        "uploaded_at": resp.uploaded_at.isoformat() if resp.uploaded_at else None,
    }


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")
    if not document_type:
        return _error(400, "Missing document_type field")
    if not file:
        return _error(400, "Missing file field in multipart request")

    service = get_document_service(db)
    try:
        size = file.size or 0
        resp = service.UploadDocument(
            None,
            x_doctor_public_id,
            document_type,
            file.file,
            file.filename or "upload.bin",
            size,
        )
        return JSONResponse(status_code=201, content=_serialize_doc(resp))
    except Exception as e:
        return _error(400, str(e))


@router.get("/documents", status_code=status.HTTP_200_OK)
async def get_documents(
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")

    service = get_document_service(db)
    try:
        docs = service.GetDoctorDocuments(None, x_doctor_public_id)
        return [_serialize_doc(d) for d in docs]
    except Exception as e:
        return _error(400, str(e))


@router.delete("/documents", status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: str = Query(...),
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")
    if not document_id:
        return _error(400, "Missing document_id parameter")

    service = get_document_service(db)
    try:
        service.DeleteDocument(None, document_id, x_doctor_public_id)
        return {"message": "Document deleted successfully"}
    except Exception as e:
        return _error(400, str(e))
