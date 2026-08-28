from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import uuid
import datetime

router = APIRouter(prefix="/api/v1/prescriptions", tags=["prescriptions"])

class CreatePrescriptionRequest(BaseModel):
    patient_id: str
    diagnosis: str
    medicines: List[str]

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_prescription(
    req: CreatePrescriptionRequest,
    x_doctor_public_id: Optional[str] = Header(None, alias="X-Doctor-Public-ID")
):
    prescription_id = str(uuid.uuid4())
    response = {
        "prescription_id": prescription_id,
        "status": "ISSUED",
        "patient_id": req.patient_id,
        "diagnosis": req.diagnosis,
        "medicines": req.medicines,
        "digital_signature": {
            "signed_by": x_doctor_public_id or "",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "algorithm": "RSA-SHA256-PKCS1v15"
        },
        "message": "Digital prescription created successfully."
    }
    return response
