from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from entities.api_key import Environment

class ApiKeyCreate(BaseModel):
    environment: Environment = Environment.TEST

class ApiKeyResponse(BaseModel):
    id: int
    company_id: int
    environment: Environment
    prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]

    class Config:
        orm_mode = True

class ApiKeyGenerateResponse(BaseModel):
    id: int
    environment: Environment
    raw_key: str
    message: str = "Store this raw_key safely. It will not be shown again."
