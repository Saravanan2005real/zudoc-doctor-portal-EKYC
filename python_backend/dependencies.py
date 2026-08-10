"""
Dependency injection and service initialization
"""
import os
from database import SessionLocal
from sqlalchemy.orm import Session

from repositories.doctor_repository import DoctorRepository
from repositories.otp_repository import OTPRepository
from repositories.refresh_token_repository import RefreshTokenRepository
from repositories.license_repository import LicenseRepository
from repositories.qualification_repository import QualificationRepository
from repositories.clinic_repository import ClinicRepository
from repositories.document_repository import DocumentRepository
from repositories.history_repository import VerificationHistoryRepository
from repositories.job_repository import JobRepository

from services.auth_service import DefaultAuthService
from services.license_service import DefaultLicenseService
from services.qualification_service import DefaultQualificationService
from services.clinic_service import DefaultClinicService
from services.document_service import DefaultDocumentService
from services.submission_service import DefaultSubmissionService
from services.ekyc_evaluation_service import DefaultEkycEvaluationService

from sms.mock import MockSMSProvider
from security.jwt import JWTManager
from security.token import RefreshTokenManager
from security.password import PasswordUtil
from security.otp import OTPUtil
from storage.local import LocalStorageProvider
from storage.validator import FileValidator
from storage.scanner import DefaultVirusScanner
from config.config import settings

_sms_provider = None
_jwt_manager = None
_refresh_token_manager = None
_password_util = None
_otp_util = None
_storage_provider = None
_file_validator = None
_virus_scanner = None


def get_sms_provider():
    global _sms_provider
    if _sms_provider is None:
        _sms_provider = MockSMSProvider()
    return _sms_provider


def get_jwt_manager():
    global _jwt_manager
    if _jwt_manager is None:
        jwt_secret = os.getenv("JWT_SECRET", "super-secret-jwt-key-2026")
        _jwt_manager = JWTManager(jwt_secret, 15)
    return _jwt_manager


def get_refresh_token_manager():
    global _refresh_token_manager
    if _refresh_token_manager is None:
        duration_days = int(os.getenv("REFRESH_TOKEN_DURATION_DAYS", "7"))
        _refresh_token_manager = RefreshTokenManager(duration_days)
    return _refresh_token_manager


def get_password_util():
    global _password_util
    if _password_util is None:
        _password_util = PasswordUtil()
    return _password_util


def get_otp_util():
    global _otp_util
    if _otp_util is None:
        _otp_util = OTPUtil()
    return _otp_util


def get_storage_provider():
    global _storage_provider
    if _storage_provider is None:
        base_dir = os.path.join(os.path.dirname(__file__), "uploads")
        _storage_provider = LocalStorageProvider(base_dir=base_dir, base_url="/uploads")
    return _storage_provider


def get_file_validator():
    global _file_validator
    if _file_validator is None:
        _file_validator = FileValidator(10 * 1024 * 1024, 300)
    return _file_validator


def get_virus_scanner():
    global _virus_scanner
    if _virus_scanner is None:
        _virus_scanner = DefaultVirusScanner()
    return _virus_scanner


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_auth_service(db: Session = None):
    if db is None:
        db = next(get_db())
    return DefaultAuthService(
        doctor_repo=DoctorRepository(db),
        otp_repo=OTPRepository(db),
        refresh_token_repo=RefreshTokenRepository(db),
        sms_provider=get_sms_provider(),
        jwt_manager=get_jwt_manager(),
        refresh_token_mgr=get_refresh_token_manager(),
        cfg=settings,
        password_util=get_password_util(),
        otp_util=get_otp_util(),
    )


def get_license_service(db: Session):
    return DefaultLicenseService(DoctorRepository(db), LicenseRepository(db))


def get_qualification_service(db: Session):
    return DefaultQualificationService(DoctorRepository(db), QualificationRepository(db))


def get_clinic_service(db: Session):
    return DefaultClinicService(DoctorRepository(db), ClinicRepository(db))


def get_document_service(db: Session):
    return DefaultDocumentService(
        doctor_repo=DoctorRepository(db),
        doc_repo=DocumentRepository(db),
        storage_provider=get_storage_provider(),
        validator=get_file_validator(),
        scanner=get_virus_scanner(),
    )


def get_submission_service(db: Session):
    return DefaultSubmissionService(
        doctor_repo=DoctorRepository(db),
        license_repo=LicenseRepository(db),
        qual_repo=QualificationRepository(db),
        clinic_repo=ClinicRepository(db),
        doc_repo=DocumentRepository(db),
        history_repo=VerificationHistoryRepository(db),
        job_repo=JobRepository(db),
    )


def get_ekyc_evaluation_service(db: Session):
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    return DefaultEkycEvaluationService(
        doctor_repo=DoctorRepository(db),
        doc_repo=DocumentRepository(db),
        history_repo=VerificationHistoryRepository(db),
        ocr_service_url=os.getenv("OCR_SERVICE_URL", "http://127.0.0.1:5001/api/v1/ocr"),
        uploads_dir=uploads_dir,
    )
