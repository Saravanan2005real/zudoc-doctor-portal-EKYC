import uuid
from datetime import datetime, timezone
from sms.provider import SMSPayload
from entities.doctor import Doctor, DoctorStatus
from entities.otp import OTPVerification, OTPPurpose
from entities.refresh_token import RefreshToken


class AuthService:
    def Register(self, ctx, req): pass
    def VerifyOTP(self, ctx, req): pass
    def Login(self, ctx, req): pass


class DefaultAuthService(AuthService):
    def __init__(self, doctor_repo, otp_repo, refresh_token_repo, sms_provider, jwt_manager, refresh_token_mgr, cfg, password_util, otp_util):
        self.doctorRepo = doctor_repo
        self.otpRepo = otp_repo
        self.refreshTokenRepo = refresh_token_repo
        self.smsProvider = sms_provider
        self.jwtManager = jwt_manager
        self.refreshTokenMgr = refresh_token_mgr
        self.cfg = cfg
        self.password_util = password_util
        self.otp_util = otp_util

    def _now(self):
        return datetime.now(timezone.utc)

    def _doctor_profile(self, doc, mobile_verified=None):
        class DoctorProfileDTO:
            pass
        profile = DoctorProfileDTO()
        profile.PublicID = doc.public_id
        profile.FirstName = doc.first_name
        profile.LastName = doc.last_name
        profile.Email = doc.email
        profile.Mobile = doc.mobile
        profile.Status = doc.status.value if hasattr(doc.status, "value") else str(doc.status)
        profile.MobileVerified = doc.mobile_verified if mobile_verified is None else mobile_verified
        profile.EmailVerified = doc.email_verified
        return profile

    def Register(self, ctx, req):
        try:
            self.password_util.ValidatePasswordPolicy(req.Password)
        except Exception as e:
            raise Exception(str(e))

        if self.doctorRepo.FindByEmail(req.Email):
            raise Exception("email address is already registered")

        if self.doctorRepo.FindByMobile(req.Mobile):
            raise Exception("mobile number is already registered")

        try:
            pwd_hash = self.password_util.HashPassword(req.Password)
        except Exception as e:
            raise Exception(f"failed to hash password: {e}")

        dob = None
        if getattr(req, "DOB", None):
            try:
                dob = datetime.strptime(req.DOB, "%Y-%m-%d")
            except ValueError:
                pass

        doc = Doctor(
            first_name=req.FirstName,
            last_name=req.LastName,
            gender=req.Gender,
            dob=dob,
            mobile=req.Mobile,
            email=req.Email,
            password_hash=pwd_hash,
            status=DoctorStatus.NOT_SUBMITTED,
            mobile_verified=False,
            email_verified=False,
        )

        try:
            self.doctorRepo.Create(doc)
        except Exception as e:
            raise Exception(f"failed to create doctor record: {e}")

        try:
            raw_otp = self.otp_util.GenerateSecureOTP(6)
        except Exception as e:
            raise Exception(f"failed to generate OTP: {e}")

        otp_entity = OTPVerification(
            doctor_id=doc.id,
            purpose=OTPPurpose.REGISTER,
            otp_hash=self.otp_util.HashOTP(raw_otp),
            expires_at=self._now() + self.cfg.OTPDuration,
            attempt_count=0,
            max_attempts=self.cfg.OTPMaxAttempts,
            is_verified=False,
        )

        try:
            self.otpRepo.Create(otp_entity)
        except Exception as e:
            raise Exception(f"failed to save OTP: {e}")

        try:
            self.smsProvider.send_otp(ctx, SMSPayload(
                mobile=doc.mobile,
                otp=raw_otp,
                purpose="REGISTER",
            ))
        except Exception:
            pass

        class RegisterResponse:
            pass
        resp = RegisterResponse()
        resp.Message = "Doctor registered successfully. OTP sent for mobile verification."
        resp.PublicID = doc.public_id
        resp.Mobile = doc.mobile
        resp.ExpiresInSeconds = int(self.cfg.OTPDuration.total_seconds())
        return resp

    def VerifyOTP(self, ctx, req):
        doc = None
        if getattr(req, "PublicID", None):
            try:
                doc = self.doctorRepo.FindByPublicID(uuid.UUID(req.PublicID))
            except ValueError:
                pass
        elif getattr(req, "Mobile", None):
            doc = self.doctorRepo.FindByMobile(req.Mobile)

        if not doc:
            raise Exception("doctor account not found")

        purpose = getattr(req, "Purpose", None) or "REGISTER"
        active_otp = self.otpRepo.FindLatestActive(doc.id, purpose)
        if not active_otp:
            raise Exception("no active OTP verification process found")

        expires_at = active_otp.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if self._now() > expires_at:
            raise Exception("OTP has expired. Please request a new OTP")

        if active_otp.attempt_count >= active_otp.max_attempts:
            raise Exception("maximum OTP verification attempts exceeded. Please request a new OTP")

        if not self.otp_util.VerifyOTP(req.OTP, active_otp.otp_hash):
            try:
                self.otpRepo.IncrementAttempt(active_otp.id)
            except Exception:
                pass
            remaining = active_otp.max_attempts - (active_otp.attempt_count + 1)
            raise Exception(f"invalid OTP. {remaining} attempts remaining")

        self.otpRepo.MarkVerified(active_otp.id)
        self.doctorRepo.MarkMobileVerified(doc.id)
        doc.mobile_verified = True

        try:
            access_token, access_expires_at = self.jwtManager.GenerateToken(
                doc.id, doc.public_id, doc.email, "DOCTOR"
            )
        except Exception as e:
            raise Exception(f"failed to generate access token: {e}")

        try:
            raw_refresh_token, refresh_hash, refresh_expires_at = self.refreshTokenMgr.GenerateRefreshToken()
        except Exception as e:
            raise Exception(f"failed to generate refresh token: {e}")

        try:
            self.refreshTokenRepo.Create(RefreshToken(
                doctor_id=doc.id,
                token_hash=refresh_hash,
                expires_at=refresh_expires_at,
                is_revoked=False,
            ))
        except Exception as e:
            raise Exception(f"failed to store refresh token: {e}")

        class AuthResponse:
            pass
        resp = AuthResponse()
        resp.Message = "Mobile number verified successfully."
        resp.AccessToken = access_token
        resp.RefreshToken = raw_refresh_token
        resp.TokenType = "Bearer"
        resp.ExpiresIn = int((access_expires_at - datetime.utcnow()).total_seconds())
        resp.MobileVerified = True
        resp.Doctor = self._doctor_profile(doc, mobile_verified=True)
        return resp

    def Login(self, ctx, req):
        doc = self.doctorRepo.FindByIdentifier(req.Identifier)
        if not doc:
            raise Exception("invalid credentials")

        if doc.status == DoctorStatus.SUSPENDED:
            raise Exception("account has been suspended. Please contact support")

        locked_until = doc.account_locked_until
        if locked_until:
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if self._now() < locked_until:
                raise Exception(
                    f"account is locked due to multiple failed login attempts. Try again in {locked_until - self._now()}"
                )

        if not self.password_util.CheckPasswordHash(req.Password, doc.password_hash):
            try:
                failed_count, is_locked = self.doctorRepo.IncrementFailedLogin(
                    doc.id, self.cfg.MaxLoginAttempts, self.cfg.AccountLockDuration
                )
                if is_locked:
                    raise Exception(
                        f"account locked due to {failed_count} consecutive failed login attempts. Try again in {self.cfg.AccountLockDuration}"
                    )
            except Exception as e:
                if "account locked" in str(e):
                    raise e
            raise Exception("invalid credentials")

        try:
            self.doctorRepo.ResetFailedLogin(doc.id)
        except Exception:
            pass

        if not doc.mobile_verified:
            try:
                raw_otp = self.otp_util.GenerateSecureOTP(6)
                try:
                    self.otpRepo.InvalidatePreviousOTPs(doc.id, "REGISTER")
                except Exception:
                    pass

                self.otpRepo.Create(OTPVerification(
                    doctor_id=doc.id,
                    purpose=OTPPurpose.REGISTER,
                    otp_hash=self.otp_util.HashOTP(raw_otp),
                    expires_at=self._now() + self.cfg.OTPDuration,
                    attempt_count=0,
                    max_attempts=self.cfg.OTPMaxAttempts,
                    is_verified=False,
                ))

                try:
                    self.smsProvider.send_otp(ctx, SMSPayload(
                        mobile=doc.mobile,
                        otp=raw_otp,
                        purpose="REGISTER",
                    ))
                except Exception:
                    pass
            except Exception:
                pass

            class AuthResponsePending:
                pass
            resp = AuthResponsePending()
            resp.Message = "Mobile verification pending. A fresh OTP has been sent to your mobile number."
            resp.MobileVerified = False
            resp.AccessToken = None
            resp.RefreshToken = None
            resp.TokenType = None
            resp.ExpiresIn = None
            resp.Doctor = self._doctor_profile(doc, mobile_verified=False)
            return resp

        try:
            access_token, access_expires_at = self.jwtManager.GenerateToken(
                doc.id, doc.public_id, doc.email, "DOCTOR"
            )
        except Exception as e:
            raise Exception(f"failed to generate access token: {e}")

        try:
            raw_refresh_token, refresh_hash, refresh_expires_at = self.refreshTokenMgr.GenerateRefreshToken()
        except Exception as e:
            raise Exception(f"failed to generate refresh token: {e}")

        try:
            self.refreshTokenRepo.Create(RefreshToken(
                doctor_id=doc.id,
                token_hash=refresh_hash,
                expires_at=refresh_expires_at,
                is_revoked=False,
            ))
        except Exception:
            pass

        class AuthResponse:
            pass
        resp = AuthResponse()
        resp.Message = "Login successful."
        resp.AccessToken = access_token
        resp.RefreshToken = raw_refresh_token
        resp.TokenType = "Bearer"
        resp.ExpiresIn = int((access_expires_at - datetime.utcnow()).total_seconds())
        resp.MobileVerified = True
        resp.Doctor = self._doctor_profile(doc, mobile_verified=True)
        return resp
