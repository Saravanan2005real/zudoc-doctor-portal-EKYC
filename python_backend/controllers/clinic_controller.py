from fastapi import APIRouter, Header, Query, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from dependencies import get_db, get_clinic_service
from dto.profile_dto import AddClinicRequest

router = APIRouter(prefix="/api/v1/doctors", tags=["clinics"])


def _error(status_code: int, message: str):
    return JSONResponse(status_code=status_code, content={"error": message})


def _serialize(resp) -> dict:
    return {
        "clinic_id": str(resp.clinic_id),
        "clinic_name": resp.clinic_name,
        "address": resp.address,
        "city": resp.city,
        "state": resp.state,
        "pincode": resp.pincode,
        "consultation_mode": resp.consultation_mode,
        "consultation_fee": float(resp.consultation_fee or 0),
        "created_at": resp.created_at.isoformat() if resp.created_at else None,
    }


@router.post("/clinics", status_code=status.HTTP_201_CREATED)
async def add_clinic(
    req: AddClinicRequest,
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")
    service = get_clinic_service(db)
    try:
        resp = service.AddClinic(None, x_doctor_public_id, req)
        return JSONResponse(status_code=201, content=_serialize(resp))
    except Exception as e:
        return _error(400, str(e))


@router.get("/clinics", status_code=status.HTTP_200_OK)
async def get_clinics(
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")
    service = get_clinic_service(db)
    try:
        return [_serialize(r) for r in service.GetClinics(None, x_doctor_public_id)]
    except Exception as e:
        return _error(400, str(e))


@router.delete("/clinics", status_code=status.HTTP_200_OK)
async def delete_clinic(
    clinic_id: str = Query(...),
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")
    service = get_clinic_service(db)
    try:
        service.DeleteClinic(None, clinic_id, x_doctor_public_id)
        return {"message": "Clinic deleted successfully"}
    except Exception as e:
        return _error(400, str(e))
