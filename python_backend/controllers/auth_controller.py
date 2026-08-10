from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from dto.auth_dto import RegisterRequest, VerifyOTPRequest, LoginRequest, RegisterResponse, AuthResponse, DoctorProfileDTO
from dependencies import get_auth_service, get_db

router = APIRouter(prefix="/api/v1/doctors", tags=["auth"])


def _error(status_code: int, message: str):
    return JSONResponse(status_code=status_code, content={"error": message})


def _to_doctor_profile(doctor) -> DoctorProfileDTO:
    return DoctorProfileDTO(
        public_id=doctor.PublicID,
        first_name=doctor.FirstName,
        last_name=doctor.LastName,
        email=doctor.Email,
        mobile=doctor.Mobile,
        status=doctor.Status,
        mobile_verified=doctor.MobileVerified,
        email_verified=doctor.EmailVerified,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    auth_service = get_auth_service(db)

    class ServiceRequest:
        def __init__(self):
            self.FirstName = req.first_name
            self.LastName = req.last_name
            self.Gender = req.gender
            self.DOB = req.dob
            self.Mobile = req.mobile
            self.Email = req.email
            self.Password = req.password

    try:
        resp = auth_service.Register(None, ServiceRequest())
        return RegisterResponse(
            message=resp.Message,
            public_id=resp.PublicID,
            mobile=resp.Mobile,
            expires_in_seconds=resp.ExpiresInSeconds,
        )
    except Exception as e:
        return _error(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/verify-otp", status_code=status.HTTP_200_OK)
async def verify_otp(req: VerifyOTPRequest, db: Session = Depends(get_db)):
    auth_service = get_auth_service(db)

    class ServiceRequest:
        def __init__(self):
            self.PublicID = req.public_id
            self.Mobile = req.mobile
            self.OTP = req.otp
            self.Purpose = req.purpose

    try:
        resp = auth_service.VerifyOTP(None, ServiceRequest())
        doctor_profile = _to_doctor_profile(resp.Doctor) if getattr(resp, "Doctor", None) else None
        return AuthResponse(
            message=resp.Message,
            access_token=getattr(resp, "AccessToken", None),
            refresh_token=getattr(resp, "RefreshToken", None),
            token_type=getattr(resp, "TokenType", None),
            expires_in=getattr(resp, "ExpiresIn", None),
            mobile_verified=resp.MobileVerified,
            doctor=doctor_profile,
        )
    except Exception as e:
        return _error(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    auth_service = get_auth_service(db)

    class ServiceRequest:
        def __init__(self):
            self.Identifier = req.identifier
            self.Password = req.password

    try:
        resp = auth_service.Login(None, ServiceRequest())
        doctor_profile = _to_doctor_profile(resp.Doctor) if getattr(resp, "Doctor", None) else None
        return AuthResponse(
            message=resp.Message,
            access_token=getattr(resp, "AccessToken", None),
            refresh_token=getattr(resp, "RefreshToken", None),
            token_type=getattr(resp, "TokenType", None),
            expires_in=getattr(resp, "ExpiresIn", None),
            mobile_verified=resp.MobileVerified,
            doctor=doctor_profile,
        )
    except Exception as e:
        return _error(status.HTTP_401_UNAUTHORIZED, str(e))
