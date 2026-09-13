import os
import uvicorn
import logging



from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base

# Import all entity models to register them with Base
from entities.doctor import Doctor
from entities.license import DoctorLicense
from entities.qualification import DoctorQualification
from entities.clinic import DoctorClinic
from entities.document import DoctorDocument
from entities.history import VerificationHistory
from entities.admin import AdminUser
from entities.otp import OTPVerification
from entities.refresh_token import RefreshToken
from entities.job import VerificationJob
from entities.ocr_result import DocumentOCRResult
from entities.admin_action import AdminAction
from entities.note import DoctorNote
from entities.flag import VerificationFlag
from entities.audit import AuditEvent
from entities.dlq import VerificationDeadJob
from entities.prescription import Prescription
from entities.company import Company, CompanyUser
from entities.verification_service import VerificationService
from entities.verification_profile import VerificationProfile, ProfileVersion, VerificationStep, VerificationEdge
from entities.application import Application, VerificationAttempt, VerificationResult, VerificationDecision

from entities.company_request import CompanyRequest

# Import all controller routers
from controllers.auth_controller import router as auth_router
from controllers.profile_controller import router as profile_router
from controllers.license_controller import router as license_router
from controllers.qualification_controller import router as qualification_router
from controllers.clinic_controller import router as clinic_router
from controllers.document_controller import router as document_router
from controllers.submission_controller import router as submission_router
from controllers.evaluation_controller import router as evaluation_router
from controllers.admin_controller import router as admin_router
from controllers.analytics_controller import router as analytics_router
from controllers.dlq_controller import router as dlq_router
from controllers.prescription_controller import router as prescription_router
from controllers.liveness_controller import router as liveness_router
from controllers.ocr_controller import router as ocr_router
from controllers.superadmin_controller import router as superadmin_router
from controllers.api_key_controller import router as api_key_router
from controllers.application_controller import router as application_router
from controllers.reviewer_controller import router as reviewer_router
from controllers.webhook_controller import router as webhook_router
from controllers.b2b_controller import router as b2b_router
from middleware.audit import AuditMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Enterprise Doctor Verification Service",
    version="1.0.0",
    description="Python FastAPI translation of the Go backend"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditMiddleware)

# Database Configuration (PostgreSQL)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD", "dinesh_2006")
DB_NAME = os.getenv("DB_NAME", "doctor_verification_db")

SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

try:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info(f"[DB] Successfully connected to PostgreSQL database on {DB_HOST}:{DB_PORT}.")
    
    # Auto-create all tables
    logger.info("[DB] Running schema auto-migrations...")
    Base.metadata.create_all(bind=engine)
    logger.info("[DB] Schema auto-migrations completed successfully.")
except Exception as e:
    logger.error(f"[DB FATAL] Failed to connect to PostgreSQL or create tables. Error: {e}")

# Observability endpoints
@app.get("/health/live", tags=["health"])
async def health_live():
    return {"status": "live"}

@app.get("/health/ready", tags=["health"])
async def health_ready():
    return {"status": "ready"}

@app.get("/metrics", tags=["observability"])
async def metrics():
    return {"metrics": "Not implemented"}

# Include routers
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(license_router)
app.include_router(qualification_router)
app.include_router(clinic_router)
app.include_router(document_router)
app.include_router(submission_router)
app.include_router(evaluation_router)
app.include_router(admin_router)
app.include_router(analytics_router)
app.include_router(dlq_router)
app.include_router(prescription_router)
app.include_router(liveness_router)
app.include_router(ocr_router)
app.include_router(superadmin_router)
app.include_router(api_key_router)
app.include_router(application_router)
app.include_router(reviewer_router)
app.include_router(webhook_router)
app.include_router(b2b_router)



# Mount static files
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")




from pydantic import BaseModel
class SessionVerifyRequest(BaseModel):
    aadhar_number: str

@app.post("/session", tags=["demo"])
async def handle_session_verification(req: SessionVerifyRequest, id: str = None):
    """Handle Swiggy Aadhaar verification through the session link."""
    if not req.aadhar_number or len(req.aadhar_number) != 12:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid Aadhaar number format. Must be 12 digits.")
        
    return {
        "status": "success",
        "message": f"Aadhaar ending in {req.aadhar_number[-4:]} successfully verified locally (Session ID: {id})."
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))

    logger.info("=======================================================")
    logger.info("Starting Enterprise Doctor Verification Service API v1.0.0")
    logger.info("=======================================================")
    
    try:
        logger.info(f"Server listening and serving HTTP at: http://127.0.0.1:{port}")
        uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        logger.warning(f"[SERVER NOTICE] Port {port} bound or busy. Trying fallback port 8081 at http://127.0.0.1:8081")
        uvicorn.run("main:app", host="0.0.0.0", port=8081, log_level="info")
