from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum
from sqlalchemy import DateTime

from database import Base

class ProfileStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    TESTING = "TESTING"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

class EdgeCondition(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    ALWAYS = "ALWAYS"

class VerificationProfile(Base):
    __tablename__ = "verification_profiles"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company = relationship("Company", back_populates="profiles")
    versions = relationship("ProfileVersion", back_populates="profile", cascade="all, delete-orphan")


class ProfileVersion(Base):
    __tablename__ = "profile_versions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("verification_profiles.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    status = Column(Enum(ProfileStatus), default=ProfileStatus.DRAFT, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    profile = relationship("VerificationProfile", back_populates="versions")
    steps = relationship("VerificationStep", back_populates="profile_version", cascade="all, delete-orphan")
    edges = relationship("VerificationEdge", back_populates="profile_version", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="profile_version")


class VerificationStep(Base):
    __tablename__ = "verification_steps"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    profile_version_id = Column(Integer, ForeignKey("profile_versions.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("verification_services.id"), nullable=False)
    node_key = Column(String, nullable=False)  # Stable key for UI graph e.g., 'aadhaar_1'
    order_index = Column(Integer, nullable=False)
    is_required = Column(Boolean, default=True, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    configuration = Column(JSON, nullable=True) # thresholds, retry logic, etc.
    
    profile_version = relationship("ProfileVersion", back_populates="steps")
    service = relationship("VerificationService", back_populates="steps")


class VerificationEdge(Base):
    __tablename__ = "verification_edges"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    profile_version_id = Column(Integer, ForeignKey("profile_versions.id"), nullable=False)
    source_step_key = Column(String, nullable=False) # References node_key of source
    target_step_key = Column(String, nullable=False) # References node_key of target
    
    # Store the advanced rule condition (e.g. {"field": "confidence", "operator": ">=", "value": 0.85})
    # If empty, implies unconditional traversal (ALWAYS)
    condition = Column(JSONB, nullable=True)

    profile_version = relationship("ProfileVersion", back_populates="edges")
