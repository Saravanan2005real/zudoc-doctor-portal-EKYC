from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from database import Base

class Role(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    REVIEWER = "REVIEWER"
    COMPANY_ADMIN = "COMPANY_ADMIN"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True) # Null for SUPER_ADMIN
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(Role), default=Role.COMPANY_ADMIN, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    company = relationship("Company")
