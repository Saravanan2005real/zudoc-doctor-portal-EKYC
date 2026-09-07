from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from database import Base

class Environment(str, enum.Enum):
    LIVE = "LIVE"
    TEST = "TEST"

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    environment = Column(Enum(Environment), default=Environment.TEST, nullable=False)
    
    # Store the prefix for UI display (e.g., sk_live_abc12...)
    prefix = Column(String(20), nullable=False)
    
    # Secure hash of the actual key using bcrypt
    key_hash = Column(String, nullable=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    company = relationship("Company")
