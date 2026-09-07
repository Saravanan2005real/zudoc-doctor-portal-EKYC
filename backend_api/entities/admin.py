import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from database import Base

class AdminRole(str, enum.Enum):
    REVIEWER = "REVIEWER"
    SENIOR_REVIEWER = "SENIOR_REVIEWER"
    SUPER_ADMIN = "SUPER_ADMIN"

class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(AdminRole, name="admin_role_enum", native_enum=False), default=AdminRole.REVIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), index=True, nullable=True)
