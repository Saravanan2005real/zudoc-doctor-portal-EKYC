from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class RegisterRequest(BaseModel):
    first_name: str = Field(...)
    last_name: str = Field(...)
    gender: Optional[str] = None
    dob: Optional[str] = Field(None, description="YYYY-MM-DD")
    mobile: str = Field(...)
    email: str = Field(...)
    password: str = Field(...)

class RegisterResponse(BaseModel):
    message: str
    public_id: UUID
    mobile: str
    expires_in_seconds: int

class VerifyOTPRequest(BaseModel):
    public_id: Optional[str] = None
    mobile: Optional[str] = None
    otp: str = Field(...)
    purpose: str = Field(...)

class LoginRequest(BaseModel):
    identifier: str = Field(...)
    password: str = Field(...)

class DoctorProfileDTO(BaseModel):
    public_id: UUID
    first_name: str
    last_name: str
    email: str
    mobile: str
    status: str
    mobile_verified: bool
    email_verified: bool

class AuthResponse(BaseModel):
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_in: Optional[int] = None
    mobile_verified: bool
    doctor: Optional[DoctorProfileDTO] = None
