from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class UpdateProfileRequest(BaseModel):
    dob: Optional[str] = Field(None, description="YYYY-MM-DD")
    gender: Optional[str] = None
    profile_photo: Optional[str] = None
    languages: Optional[str] = None
    biography: Optional[str] = None

class AddLicenseRequest(BaseModel):
    registration_number: str = Field(...)
    registration_council: str = Field(...)
    registration_year: int = Field(...)
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None

class LicenseResponse(BaseModel):
    license_id: UUID
    registration_number: str
    registration_council: str
    registration_year: int
    license_status: str
    verification_status: str
    created_at: datetime

class AddQualificationRequest(BaseModel):
    degree: str = Field(...)
    specialization: Optional[str] = None
    college: str = Field(...)
    university: str = Field(...)
    year_completed: int = Field(...)

class QualificationResponse(BaseModel):
    qualification_id: UUID
    degree: str
    specialization: str
    college: str
    university: str
    year_completed: int
    created_at: datetime

class AddClinicRequest(BaseModel):
    clinic_name: str = Field(...)
    address: str = Field(...)
    city: str = Field(...)
    state: str = Field(...)
    pincode: str = Field(...)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    consultation_mode: str = Field(...)
    consultation_fee: Optional[float] = None

class ClinicResponse(BaseModel):
    clinic_id: UUID
    clinic_name: str
    address: str
    city: str
    state: str
    pincode: str
    consultation_mode: str
    consultation_fee: float
    created_at: datetime

class DocumentUploadResponse(BaseModel):
    document_id: UUID
    doctor_id: UUID
    document_type: str
    file_url: str
    original_filename: str
    mime_type: str
    file_size: int
    file_hash: str
    version: int
    is_latest: bool
    ocr_status: str
    uploaded_at: datetime

class SubmitVerificationResponse(BaseModel):
    message: str
    public_id: UUID
    status: str
    submitted_at: datetime
