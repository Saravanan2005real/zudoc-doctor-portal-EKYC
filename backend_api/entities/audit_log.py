from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from database import Base

class AuditLog(Base):
    """
    Immutable ledger of administrative and sensitive operations.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True) # Nullable for Super Admin actions
    
    action = Column(String, nullable=False, index=True) # e.g. "publish_profile", "generate_api_key"
    resource_type = Column(String, nullable=False) # e.g. "ProfileVersion", "Company"
    resource_id = Column(Integer, nullable=True)
    
    metadata_info = Column(JSONB, nullable=True) # Renamed from metadata to avoid SQLAlchemy conflicts
    ip_address = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    actor = relationship("User")
    company = relationship("Company")
