from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from entities.application import Application, VerificationDecision
from entities.user import User, Role
from security.auth import get_current_user, require_role

from dto.application_dto import ApplicationListResponse, ApplicationDetailResponse, VerificationAttemptResponse

router = APIRouter(prefix="/api/v1/admin/applications", tags=["Application Monitoring"])

@router.get("", response_model=List[ApplicationListResponse])
def list_applications(
    company_id: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(Application)
    
    if company_id:
        query = query.filter(Application.company_id == company_id)
        
    return query.all()

@router.get("/{application_id}", response_model=ApplicationDetailResponse)
def get_application_details(
    application_id: int,
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    decision = db.query(VerificationDecision).filter(VerificationDecision.application_id == application_id).first()
    
    attempts_dto = [
        VerificationAttemptResponse(
            id=a.id,
            step_key=a.step_key,
            status=a.status.value,
            started_at=a.started_at,
            completed_at=a.completed_at
        ) for a in application.attempts
    ]
    
    return ApplicationDetailResponse(
        id=application.id,
        company_id=application.company_id,
        profile_version_id=application.profile_version_id,
        status=application.status,
        created_at=application.created_at,
        updated_at=application.updated_at,
        attempts=attempts_dto,
        final_decision=decision.decision if decision else None,
        decision_reason=decision.reason if decision else None
    )
