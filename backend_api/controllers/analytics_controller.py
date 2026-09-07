from fastapi import APIRouter, Query, HTTPException, status, Depends
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date

from database import get_db
from entities.company import Company, CompanyStatus
from entities.application import Application, ApplicationStatus, VerificationDecision, FinalDecision

router = APIRouter(prefix="/api/v1/admin", tags=["analytics"])

@router.get("/search", status_code=status.HTTP_200_OK)
async def search(
    q: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    council: Optional[str] = Query(None),
    status_param: Optional[str] = Query(None, alias="status"),
    page: int = Query(0),
    page_size: int = Query(0)
):
    return {"message": "Search results"}

@router.get("/analytics", status_code=status.HTTP_200_OK)
async def get_analytics():
    return {"message": "Analytics data"}

@router.get("/dashboard-stats", status_code=status.HTTP_200_OK)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    total_companies = db.query(func.count(Company.id)).scalar() or 0
    active_clients = db.query(func.count(Company.id)).filter(Company.status == CompanyStatus.ACTIVE).scalar() or 0
    
    # Verified today
    today = date.today()
    verified_today = db.query(func.count(VerificationDecision.id)).filter(
        func.date(VerificationDecision.decided_at) == today,
        VerificationDecision.decision == FinalDecision.APPROVED
    ).scalar() or 0
    
    # Manual review pending
    manual_review = db.query(func.count(Application.id)).filter(
        Application.status == ApplicationStatus.REVIEW
    ).scalar() or 0
    
    # Service utilization (Mocked for now as we don't have enough data history yet)
    # Could query VerificationAttempt by step_key / service_name in the future
    service_utilization = [
        {"name": "Human Verification", "percentage": 72},
        {"name": "Aadhaar + Face Match", "percentage": 48},
        {"name": "Liveness", "percentage": 31}
    ]
    
    return {
        "total_companies": total_companies,
        "active_clients": active_clients,
        "verified_today": verified_today,
        "manual_review": manual_review,
        "service_utilization": service_utilization
    }
