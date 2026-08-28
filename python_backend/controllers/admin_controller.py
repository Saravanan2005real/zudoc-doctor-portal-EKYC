from fastapi import APIRouter, Header, Query, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

class ApproveDoctorRequest(BaseModel):
    pass

class RejectDoctorRequest(BaseModel):
    reason: str

class RequestDocumentsRequest(BaseModel):
    pass

class AddNoteRequest(BaseModel):
    note: str

@router.get("/verifications/detail", status_code=status.HTTP_200_OK)
async def get_doctor_verification_detail(id: str = Query(...)):
    if not id:
        raise HTTPException(status_code=400, detail="Missing doctor id parameter")
    return {"message": "Doctor verification detail retrieved"}

@router.post("/verifications/assign", status_code=status.HTTP_200_OK)
async def assign_doctor(
    id: str = Query(...),
    x_admin_id: Optional[str] = Header(None, alias="X-Admin-ID")
):
    if not id:
        raise HTTPException(status_code=400, detail="Invalid doctor id")
    return {"message": "Doctor verification case assigned successfully"}

@router.post("/verifications/approve", status_code=status.HTTP_200_OK)
async def approve_doctor(
    req: ApproveDoctorRequest,
    request: Request,
    id: str = Query(...),
    x_admin_id: Optional[str] = Header(None, alias="X-Admin-ID")
):
    if not id:
        raise HTTPException(status_code=400, detail="Invalid doctor id")
    return {"message": "Doctor verification approved successfully. Digital prescription features enabled."}

@router.post("/verifications/reject", status_code=status.HTTP_200_OK)
async def reject_doctor(
    req: RejectDoctorRequest,
    request: Request,
    id: str = Query(...),
    x_admin_id: Optional[str] = Header(None, alias="X-Admin-ID")
):
    if not id:
        raise HTTPException(status_code=400, detail="Invalid doctor id")
    if not req.reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    return {"message": "Doctor verification application rejected."}

@router.post("/verifications/request-documents", status_code=status.HTTP_200_OK)
async def request_documents(
    req: RequestDocumentsRequest,
    request: Request,
    id: str = Query(...),
    x_admin_id: Optional[str] = Header(None, alias="X-Admin-ID")
):
    if not id:
        raise HTTPException(status_code=400, detail="Invalid doctor id")
    return {"message": "Additional document request dispatched to doctor."}

@router.post("/verifications/notes", status_code=status.HTTP_201_CREATED)
async def add_note(
    req: AddNoteRequest,
    id: str = Query(...),
    x_admin_id: Optional[str] = Header(None, alias="X-Admin-ID")
):
    if not id:
        raise HTTPException(status_code=400, detail="Invalid doctor id")
    if not req.note:
        raise HTTPException(status_code=400, detail="Note text is required")
    return {"message": "Note added successfully"}
