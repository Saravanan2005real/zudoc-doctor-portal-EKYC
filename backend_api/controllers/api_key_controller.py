import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from entities.api_key import ApiKey, Environment
from entities.user import User, Role
from security.auth import get_password_hash, verify_password, get_current_user, require_role

from dto.api_key_dto import ApiKeyCreate, ApiKeyResponse, ApiKeyGenerateResponse

router = APIRouter(prefix="/api/v1/companies/{company_id}/api-keys", tags=["API Keys"])

# Endpoint for Super Admin or Company Admin to generate a key
@router.post("", response_model=ApiKeyGenerateResponse, status_code=status.HTTP_201_CREATED)
def generate_api_key(
    company_id: int, 
    payload: ApiKeyCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.ADMIN, Role.COMPANY_ADMIN]))
):
    # If Company Admin, ensure they belong to this company
    if current_user.role == Role.COMPANY_ADMIN and current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Not authorized to generate keys for this company")

    # Generate raw key
    raw_token = secrets.token_urlsafe(32)
    env_prefix = "sk_live_" if payload.environment == Environment.LIVE else "sk_test_"
    full_raw_key = f"{env_prefix}{raw_token}"
    
    # Store prefix and hash
    prefix = full_raw_key[:16] # Store up to first 16 chars for UI display
    key_hash = get_password_hash(full_raw_key)

    api_key = ApiKey(
        company_id=company_id,
        environment=payload.environment,
        prefix=prefix,
        key_hash=key_hash,
        is_active=True
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return ApiKeyGenerateResponse(
        id=api_key.id,
        environment=api_key.environment,
        raw_key=full_raw_key
    )

@router.get("", response_model=List[ApiKeyResponse])
def list_api_keys(
    company_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.ADMIN, Role.COMPANY_ADMIN]))
):
    if current_user.role == Role.COMPANY_ADMIN and current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Not authorized to view keys for this company")
        
    keys = db.query(ApiKey).filter(ApiKey.company_id == company_id).all()
    return keys

@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    company_id: int, 
    key_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.ADMIN, Role.COMPANY_ADMIN]))
):
    if current_user.role == Role.COMPANY_ADMIN and current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Not authorized to revoke keys for this company")
        
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.company_id == company_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key not found")
        
    api_key.is_active = False
    db.delete(api_key) # Or soft delete
    db.commit()
    return


# --- API Key Middleware ---
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

def verify_api_key(api_key_header: str = Security(api_key_header), db: Session = Depends(get_db)):
    if not api_key_header:
        raise HTTPException(status_code=401, detail="Missing API Key")
        
    # Expect format: "Bearer sk_test_..." or just "sk_test_..."
    raw_key = api_key_header.replace("Bearer ", "").strip()
    
    # Simple check on prefix to narrow down search (optimization)
    prefix = raw_key[:16]
    possible_keys = db.query(ApiKey).filter(ApiKey.prefix == prefix, ApiKey.is_active == True).all()
    
    for key in possible_keys:
        if verify_password(raw_key, key.key_hash):
            from datetime import datetime
            key.last_used_at = datetime.utcnow()
            db.commit()
            return key
            
    raise HTTPException(status_code=401, detail="Invalid API Key")
