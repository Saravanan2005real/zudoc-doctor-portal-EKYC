from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from entities.application import Application, ApplicationStatus, VerificationDecision
from entities.user import User, Role
from security.auth import get_current_user, require_role

from dto.application_dto import ApplicationListResponse
from dto.reviewer_dto import ReviewDecisionRequest

router = APIRouter(prefix="/api/v1/review", tags=["Human Review"])

@router.get("/queue", response_model=List[ApplicationListResponse])
def get_review_queue(
    db: Session = Depends(get_db)
):
    # Fetch all applications that are in REVIEW status
    applications = db.query(Application).filter(Application.status == ApplicationStatus.REVIEW).all()
    return applications

@router.post("/applications/{application_id}/decide")
def submit_review_decision(
    application_id: int,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
        
    if application.status != ApplicationStatus.REVIEW:
        raise HTTPException(status_code=400, detail="Application is not pending human review")

    # Record the final manual decision
    decision = VerificationDecision(
        company_id=application.company_id,
        application_id=application.id,
        decision=payload.decision,
        reason=payload.reason,
        confidence_score=1.0 # 100% confidence for human decisions
    )
    db.add(decision)
    
    # Update application status based on final decision
    if payload.decision == payload.decision.APPROVED:
        application.status = ApplicationStatus.APPROVED
    elif payload.decision == payload.decision.REJECTED:
        application.status = ApplicationStatus.REJECTED
    elif payload.decision == payload.decision.FAILED:
        application.status = ApplicationStatus.FAILED
    # IF REQUEST_INFO, maybe stay in REVIEW or switch to PENDING

    db.commit()
    return {"message": f"Application {payload.decision.value} successfully"}
