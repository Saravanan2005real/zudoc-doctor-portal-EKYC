import string
import random
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy.orm import Session
from database import SessionLocal

from entities.company_request import CompanyRequest, RequestStatus
from entities.company import Company, CompanyStatus, CompanyUser
from entities.api_key import ApiKey, Environment

router = APIRouter(prefix="/api/v1/b2b", tags=["b2b"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---- Request Models ----

class CompanyRequestSubmit(BaseModel):
    company_name: str
    contact_name: str
    contact_email: EmailStr
    industry: str
    expected_volume: str
    requirements: Optional[str] = None

class ApproveRequest(BaseModel):
    pass

class AadharVerifyRequest(BaseModel):
    aadhar_number: str

# ---- Public Routes ----

@router.post("/requests")
def submit_company_request(req: CompanyRequestSubmit, db: Session = Depends(get_db)):
    """Public endpoint for companies to submit a request for API access."""
    new_req = CompanyRequest(
        company_name=req.company_name,
        contact_name=req.contact_name,
        contact_email=req.contact_email,
        industry=req.industry,
        expected_volume=req.expected_volume,
        requirements=req.requirements
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    return {"status": "success", "message": "Request submitted successfully. Our team will review it shortly.", "request_id": new_req.id}

@router.post("/verify-aadhar")
def verify_aadhar_locally(req: AadharVerifyRequest):
    """Locally verify an Aadhaar number for Swiggy Demo."""
    # Simple validation for demo
    if len(req.aadhar_number) != 12 or not req.aadhar_number.isdigit():
        raise HTTPException(status_code=400, detail="Invalid Aadhaar number format. Must be 12 digits.")
    
    # Simulate a local verification check
    return {
        "status": "success",
        "message": f"Aadhaar number ending in {req.aadhar_number[-4:]} has been successfully verified."
    }

# ---- Admin Routes ----

@router.get("/admin/requests")
def list_requests(db: Session = Depends(get_db)):
    """List all company requests for the admin dashboard."""
    requests = db.query(CompanyRequest).order_by(CompanyRequest.created_at.desc()).all()
    return {"status": "success", "data": requests}

@router.post("/admin/requests/{request_id}/approve")
def approve_request(request_id: int, req: ApproveRequest, db: Session = Depends(get_db)):
    """Approve a company request. Creates Company, User, and API Key."""
    db_req = db.query(CompanyRequest).filter(CompanyRequest.id == request_id).first()
    if not db_req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if db_req.status != RequestStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Request is already {db_req.status}")

    db_req.status = RequestStatus.APPROVED
    
    # Create the actual Company record
    new_company = Company(
        name=db_req.company_name,
        industry=db_req.industry,
        status=CompanyStatus.ACTIVE
    )
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    
    # Generate API Key
    # Format: sk_live_XXXXXXXXXXXXXXXXXXXX
    raw_key = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    raw_key_full = f"sk_live_{raw_key}"
    prefix = raw_key_full[:15]
    
    # In a real app we bcrypt hash the key here. For demo, we just store it raw 
    # to show the admin, or hash it and just return it once.
    new_api_key = ApiKey(
        company_id=new_company.id,
        environment=Environment.LIVE,
        prefix=prefix,
        key_hash=raw_key_full, # Demoware: storing raw so we can use it
        is_active=True
    )
    db.add(new_api_key)
    db.commit()
    
    return {
        "status": "success",
        "message": "Company approved and API Key generated.",
        "company_id": new_company.id,
        "api_key": raw_key_full
    }
