from sqlalchemy import Column, Integer, String, Boolean
from database import Base
from sqlalchemy.orm import relationship

class VerificationService(Base):
    """
    Registry of available verification services (e.g., AADHAAR, FACE_MATCH, HUMAN_REVIEW)
    """
    __tablename__ = "verification_services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    is_configurable = Column(Boolean, default=True, nullable=False)
    provider_adapter = Column(String, nullable=True) # e.g. 'aws_rekognition'

    steps = relationship("VerificationStep", back_populates="service")
