from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, Enum, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from database import Base

class ApplicationStatus(str, enum.Enum):
    PENDING = "PENDING"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"

class AttemptStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class StepDecision(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"

class FinalDecision(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    FAILED = "FAILED"

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    profile_version_id = Column(Integer, ForeignKey("profile_versions.id"), nullable=False)
    applicant_identifier = Column(String, nullable=False) # External ID or email
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.PENDING, nullable=False)
    risk_level = Column(String, nullable=True) # HIGH, MEDIUM, LOW
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company = relationship("Company", back_populates="applications")
    profile_version = relationship("ProfileVersion", back_populates="applications")
    attempts = relationship("VerificationAttempt", back_populates="application", cascade="all, delete-orphan")
    decision = relationship("VerificationDecision", uselist=False, back_populates="application", cascade="all, delete-orphan")


class VerificationAttempt(Base):
    __tablename__ = "verification_attempts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    step_key = Column(String, nullable=False) # Node key from the graph executed
    status = Column(Enum(AttemptStatus), default=AttemptStatus.PENDING, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    application = relationship("Application", back_populates="attempts")
    result = relationship("VerificationResult", uselist=False, back_populates="attempt", cascade="all, delete-orphan")


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    attempt_id = Column(Integer, ForeignKey("verification_attempts.id"), nullable=False)
    confidence_score = Column(Float, nullable=True)
    raw_response = Column(JSON, nullable=True)
    decision = Column(Enum(StepDecision), nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    attempt = relationship("VerificationAttempt", back_populates="result")


class VerificationDecision(Base):
    __tablename__ = "verification_decisions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, unique=True)
    decision = Column(Enum(FinalDecision), nullable=False)
    reason = Column(String, nullable=True)
    risk_level = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    decided_at = Column(DateTime(timezone=True), server_default=func.now())

    application = relationship("Application", back_populates="decision")
