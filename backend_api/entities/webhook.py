from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from database import Base

class WebhookEventType(str, enum.Enum):
    VERIFICATION_STARTED = "verification.started"
    VERIFICATION_STEP_COMPLETED = "verification.step.completed"
    VERIFICATION_REVIEW_REQUIRED = "verification.review.required"
    VERIFICATION_COMPLETED = "verification.completed"
    VERIFICATION_APPROVED = "verification.approved"
    VERIFICATION_REJECTED = "verification.rejected"

class WebhookDeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    url = Column(String, nullable=False)
    secret_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    subscribed_events = Column(ARRAY(String), nullable=False) # e.g. ["verification.started", "verification.completed"]
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    company = relationship("Company")


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("webhook_endpoints.id"), nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    
    event_type = Column(String, nullable=False)
    payload = Column(JSONB, nullable=False)
    
    status = Column(Enum(WebhookDeliveryStatus), default=WebhookDeliveryStatus.PENDING)
    attempt_count = Column(Integer, default=0)
    response_code = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    
    endpoint = relationship("WebhookEndpoint")
    application = relationship("Application")
