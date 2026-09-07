from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from entities.application import ApplicationStatus, FinalDecision

class ApplicationListResponse(BaseModel):
    id: int
    company_id: int
    profile_version_id: int
    status: ApplicationStatus
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

class VerificationAttemptResponse(BaseModel):
    id: int
    step_key: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        orm_mode = True

class ApplicationDetailResponse(BaseModel):
    id: int
    company_id: int
    profile_version_id: int
    status: ApplicationStatus
    created_at: datetime
    updated_at: Optional[datetime]
    attempts: List[VerificationAttemptResponse] = []
    final_decision: Optional[FinalDecision] = None
    decision_reason: Optional[str] = None

    class Config:
        orm_mode = True
