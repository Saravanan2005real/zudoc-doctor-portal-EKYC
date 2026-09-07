from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class WebhookEndpointCreate(BaseModel):
    url: str
    subscribed_events: List[str]

class WebhookEndpointResponse(BaseModel):
    id: int
    company_id: int
    url: str
    is_active: bool
    subscribed_events: List[str]
    created_at: datetime

    class Config:
        orm_mode = True

class WebhookEndpointCreateResponse(WebhookEndpointResponse):
    secret: str
    message: str = "Store this secret safely. It will not be shown again. Use it to verify ZuDoc-Signature."

class WebhookDeliveryResponse(BaseModel):
    id: int
    endpoint_id: int
    application_id: int
    event_type: str
    status: str
    attempt_count: int
    response_code: Optional[int]
    created_at: datetime
    delivered_at: Optional[datetime]

    class Config:
        orm_mode = True
