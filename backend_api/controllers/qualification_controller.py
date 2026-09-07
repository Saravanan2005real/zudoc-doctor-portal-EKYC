from fastapi import APIRouter, Header, Query, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from dependencies import get_db, get_qualification_service
from dto.profile_dto import AddQualificationRequest

router = APIRouter(prefix="/api/v1/doctors", tags=["qualifications"])


def _error(status_code: int, message: str):
    return JSONResponse(status_code=status_code, content={"error": message})


def _serialize(resp) -> dict:
    return {
        "qualification_id": str(resp.qualification_id),
        "degree": resp.degree,
        "specialization": resp.specialization,
        "college": resp.college,
        "university": resp.university,
        "year_completed": resp.year_completed,
        "created_at": resp.created_at.isoformat() if resp.created_at else None,
    }


@router.post("/qualifications", status_code=status.HTTP_201_CREATED)
async def add_qualification(
    req: AddQualificationRequest,
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")
    service = get_qualification_service(db)
    try:
        resp = service.AddQualification(None, x_doctor_public_id, req)
        return JSONResponse(status_code=201, content=_serialize(resp))
    except Exception as e:
        return _error(400, str(e))


@router.get("/qualifications", status_code=status.HTTP_200_OK)
async def get_qualifications(
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")
    service = get_qualification_service(db)
    try:
        return [_serialize(r) for r in service.GetQualifications(None, x_doctor_public_id)]
    except Exception as e:
        return _error(400, str(e))


@router.delete("/qualifications", status_code=status.HTTP_200_OK)
async def delete_qualification(
    qualification_id: str = Query(...),
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")
    service = get_qualification_service(db)
    try:
        service.DeleteQualification(None, qualification_id, x_doctor_public_id)
        return {"message": "Qualification deleted successfully"}
    except Exception as e:
        return _error(400, str(e))
