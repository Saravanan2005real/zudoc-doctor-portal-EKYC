from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from entities.company import CompanyStatus
from entities.verification_profile import ProfileStatus, EdgeCondition

# --- Company DTOs ---
class CompanyCreate(BaseModel):
    name: str = Field(..., example="ABC Healthcare")
    industry: Optional[str] = Field(None, example="Healthcare")

class CompanyResponse(BaseModel):
    id: int
    name: str
    industry: Optional[str]
    status: CompanyStatus
    created_at: datetime

    class Config:
        orm_mode = True

# --- Service Registry DTOs ---
class VerificationServiceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_enabled: bool
    is_configurable: bool

    class Config:
        orm_mode = True

# --- Profile DTOs ---
class ProfileCreate(BaseModel):
    name: str = Field(..., example="Doctor KYC")
    description: Optional[str] = None

class ProfileVersionResponse(BaseModel):
    id: int
    version_number: int
    status: ProfileStatus
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

class ProfileResponse(BaseModel):
    id: int
    company_id: int
    name: str
    description: Optional[str]
    created_at: datetime
    versions: List[ProfileVersionResponse] = []

    class Config:
        orm_mode = True

# --- Visual Builder Flow DTOs ---
class StepDTO(BaseModel):
    node_key: str
    service_id: int
    order_index: int
    is_required: bool = True
    is_enabled: bool = True
    configuration: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True

class EdgeDTO(BaseModel):
    source_step_key: str
    target_step_key: str
    condition: EdgeCondition = EdgeCondition.SUCCESS

    class Config:
        orm_mode = True

class FlowGraphUpdate(BaseModel):
    nodes: List[StepDTO]
    edges: List[EdgeDTO]

class FlowGraphResponse(BaseModel):
    nodes: List[StepDTO]
    edges: List[EdgeDTO]
