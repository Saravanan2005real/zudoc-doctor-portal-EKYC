from fastapi import APIRouter, Header, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from dependencies import get_db, get_submission_service

router = APIRouter(prefix="/api/v1/doctors", tags=["submission"])


def _error(status_code: int, message: str):
    return JSONResponse(status_code=status_code, content={"error": message})


@router.post("/submit-verification", status_code=status.HTTP_200_OK)
async def submit_verification(
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")

    service = get_submission_service(db)
    try:
        resp = service.SubmitVerification(None, x_doctor_public_id)
        return {
            "message": resp.message,
            "public_id": str(resp.public_id),
            "status": resp.status,
            "submitted_at": resp.submitted_at.isoformat() if resp.submitted_at else None,
        }
    except Exception as e:
        return _error(400, str(e))
