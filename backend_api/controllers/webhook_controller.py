import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from entities.webhook import WebhookEndpoint, WebhookDelivery
from entities.user import User, Role
from security.auth import get_current_user, require_role, get_password_hash

from dto.webhook_dto import WebhookEndpointCreate, WebhookEndpointResponse, WebhookEndpointCreateResponse, WebhookDeliveryResponse

router = APIRouter(prefix="/api/v1/companies/{company_id}/webhooks", tags=["Webhooks"])

@router.post("", response_model=WebhookEndpointCreateResponse, status_code=status.HTTP_201_CREATED)
def create_webhook_endpoint(
    company_id: int, 
    payload: WebhookEndpointCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.ADMIN, Role.COMPANY_ADMIN]))
):
    if current_user.role == Role.COMPANY_ADMIN and current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Not authorized to create webhooks for this company")

    # Generate a secure signing secret
    secret = secrets.token_urlsafe(32)
    # Ideally store encrypted. For now, we store hash to prevent exposure (though we need it for signing...
    # wait, if we hash it we can't use it for HMAC signing! We need to store it symmetrically encrypted or plaintext for the dispatcher to read it.
    # We will store it directly here for the MVP, or use AES in production).
    
    endpoint = WebhookEndpoint(
        company_id=company_id,
        url=payload.url,
        secret_hash=secret, # Storing raw for MVP so dispatcher can read it. Should be encrypted!
        is_active=True,
        subscribed_events=payload.subscribed_events
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    
    response_data = WebhookEndpointCreateResponse.from_orm(endpoint)
    response_data.secret = secret
    return response_data

@router.get("", response_model=List[WebhookEndpointResponse])
def list_webhook_endpoints(
    company_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.ADMIN, Role.COMPANY_ADMIN]))
):
    if current_user.role == Role.COMPANY_ADMIN and current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    endpoints = db.query(WebhookEndpoint).filter(WebhookEndpoint.company_id == company_id).all()
    return endpoints

@router.get("/deliveries", response_model=List[WebhookDeliveryResponse])
def list_webhook_deliveries(
    company_id: int, 
    endpoint_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.ADMIN, Role.COMPANY_ADMIN]))
):
    if current_user.role == Role.COMPANY_ADMIN and current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    query = db.query(WebhookDelivery).join(WebhookEndpoint).filter(WebhookEndpoint.company_id == company_id)
    if endpoint_id:
        query = query.filter(WebhookDelivery.endpoint_id == endpoint_id)
        
    return query.order_by(WebhookDelivery.created_at.desc()).limit(100).all()
