from fastapi import APIRouter, Header, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import asyncio
from dependencies import get_db, get_ekyc_evaluation_service

router = APIRouter(prefix="/api/v1/doctors", tags=["ekyc-evaluation"])


class EvaluateEkycRequest(BaseModel):
    # When provided, only these documents are evaluated. Keeps results scoped to
    # the current session instead of every document ever vaulted by the doctor.
    document_ids: Optional[List[str]] = None


def _error(status_code: int, message: str):
    return JSONResponse(status_code=status_code, content={"error": message})


@router.post("/evaluate-ekyc", status_code=status.HTTP_200_OK)
async def evaluate_ekyc(
    payload: Optional[EvaluateEkycRequest] = None,
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    """
    Step 4 evaluation:
    Runs uploaded KYC documents through in-process OCR and returns
    a staged decision used by the portal before unlocking Step 5.
    """
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")

    document_ids = payload.document_ids if payload else None
    service = get_ekyc_evaluation_service(db)
    try:
        result = await asyncio.to_thread(service.Evaluate, x_doctor_public_id, document_ids)
        return result
    except Exception as e:
        return _error(400, str(e))
