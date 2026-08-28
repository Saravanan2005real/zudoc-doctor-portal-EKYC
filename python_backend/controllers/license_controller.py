from fastapi import APIRouter, Header, Query, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from dependencies import get_db, get_license_service
from dto.profile_dto import AddLicenseRequest

router = APIRouter(prefix="/api/v1/doctors", tags=["licenses"])


def _error(status_code: int, message: str):
    return JSONResponse(status_code=status_code, content={"error": message})


def _serialize(resp) -> dict:
    return {
        "license_id": str(resp.license_id),
        "registration_number": resp.registration_number,
        "registration_council": resp.registration_council,
        "registration_year": resp.registration_year,
        "license_status": resp.license_status,
        "verification_status": resp.verification_status,
        "created_at": resp.created_at.isoformat() if resp.created_at else None,
    }


@router.post("/licenses", status_code=status.HTTP_201_CREATED)
async def add_license(
    req: AddLicenseRequest,
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")
    service = get_license_service(db)
    try:
        resp = service.AddLicense(None, x_doctor_public_id, req)
        return JSONResponse(status_code=201, content=_serialize(resp))
    except Exception as e:
        return _error(400, str(e))


@router.get("/licenses", status_code=status.HTTP_200_OK)
async def get_licenses(
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")
    service = get_license_service(db)
    try:
        return [_serialize(r) for r in service.GetLicenses(None, x_doctor_public_id)]
    except Exception as e:
        return _error(400, str(e))


@router.delete("/licenses", status_code=status.HTTP_200_OK)
async def delete_license(
    license_id: str = Query(...),
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID"),
    db: Session = Depends(get_db),
):
    if not x_doctor_public_id:
        return _error(400, "Missing or invalid X-Doctor-Public-ID header")
    service = get_license_service(db)
    try:
        service.DeleteLicense(None, license_id, x_doctor_public_id)
        return {"message": "License deleted successfully"}
    except Exception as e:
        return _error(400, str(e))
