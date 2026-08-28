from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from .auth_dto import DoctorProfileDTO
from .profile_dto import (
    LicenseResponse,
    QualificationResponse,
    ClinicResponse,
    DocumentUploadResponse,
)

# Assuming these entities will be available in the python_backend.entities module
try:
    from entities import (
        DocumentOCRResult,
        VerificationFlag,
        VerificationHistory,
        AdminAction,
        DoctorNote,
    )
except ImportError:
    # Fallback types if entities are not yet translated
    from typing import Any
    DocumentOCRResult = Any
    VerificationFlag = Any
    VerificationHistory = Any
    AdminAction = Any
    DoctorNote = Any

class AdminDoctorListItem(BaseModel):
    public_id: UUID
    doctor_name: str
    email: str
    mobile: str
    status: str
    fraud_score: int
    risk_category: str
    assigned_admin_id: Optional[UUID] = None
    prescription_enabled: bool
    unresolved_flags_count: int
    created_at: datetime

class AdminDashboardResponse(BaseModel):
    total_doctors: int
    page: int
    page_size: int
    total_pages: int
    doctors: List[AdminDoctorListItem]

class SideBySideComparisonRow(BaseModel):
    field: str
    doctor_entered: str
    ocr_extracted: str
    match_score: float
    is_match: bool

class DoctorVerificationDetailResponse(BaseModel):
    profile: DoctorProfileDTO
    assigned_admin_id: Optional[UUID] = None
    assigned_at: Optional[datetime] = None
    prescription_enabled: bool
    licenses: List[LicenseResponse]
    qualifications: List[QualificationResponse]
    clinics: List[ClinicResponse]
    documents: List[DocumentUploadResponse]
    ocr_results: List[DocumentOCRResult]
    side_by_side_comparison: List[SideBySideComparisonRow]
    fraud_score: int
    risk_category: str
    flags: List[VerificationFlag]
    timeline: List[VerificationHistory]
    admin_actions: List[AdminAction]
    notes: List[DoctorNote]

class ApproveDoctorRequest(BaseModel):
    reason: Optional[str] = None

class RejectDoctorRequest(BaseModel):
    reason: str = Field(...)

class RequestDocumentsRequest(BaseModel):
    required_documents: List[str] = Field(...)
    message: str = Field(...)

class AddNoteRequest(BaseModel):
    note: str = Field(...)
    visibility: Optional[str] = Field(None, description='"INTERNAL", "VISIBLE_TO_DOCTOR"')
