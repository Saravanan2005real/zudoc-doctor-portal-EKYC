from fastapi import APIRouter, Header, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from dependencies import get_db, get_ekyc_evaluation_service

router = APIRouter(prefix="/api/v1/doctors", tags=["ekyc-evaluation"])


def _error(status_code: int, message: str):
    return JSONResponse(status_code=status_code, content={"error": message})


@router.post("/evaluate-ekyc", status_code=status.HTTP_200_OK)
async def evaluate_ekyc(
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    """
    Step 4 evaluation:
    Runs uploaded KYC documents through the OCR microservice and returns
    a staged decision used by the portal before unlocking Step 5.
    """
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")

    service = get_ekyc_evaluation_service(db)
    try:
        result = service.Evaluate(x_doctor_public_id)
        return result
    except Exception as e:
        return _error(400, str(e))
