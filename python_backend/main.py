import os
import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Mount static files
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

os.makedirs("public", exist_ok=True)
app.mount("/", StaticFiles(directory="public", html=True), name="public")


def _ocr_already_running() -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:5001/health", timeout=2) as resp:
            return resp.status < 500
    except Exception:
        try:
            import urllib.request
            with urllib.request.urlopen("http://127.0.0.1:5001/", timeout=2) as resp:
                return resp.status < 500
        except Exception:
            return False


def _ensure_ocr_process():
    """OCR must stay in a separate process (it mocks torch for Paddle)."""
    if _ocr_already_running():
        logger.info("[OCR] Microservice already running on http://127.0.0.1:5001")
        return
    import subprocess
    import sys
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info("[OCR] Starting OCR microservice on port 5001...")
    log_path = os.path.join(backend_dir, "ocr_service.log")
    log_file = open(log_path, "a", encoding="utf-8")
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(
        [sys.executable, "-m", "ocr.engine"],
        cwd=backend_dir,
        stdout=log_file,
        stderr=log_file,
        creationflags=creationflags,
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    _ensure_ocr_process()

    logger.info("=======================================================")
    logger.info("Starting Enterprise Doctor Verification Service v1.0.0")
    logger.info("=======================================================")
    
    try:
        logger.info(f"Server listening and serving HTTP on port {port}...")
        uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        logger.warning(f"[SERVER NOTICE] Port {port} bound or busy. Trying fallback port 8081...")
        uvicorn.run("main:app", host="0.0.0.0", port=8081, log_level="info")
