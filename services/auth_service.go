package services

import (
	"context"
	"errors"
	"fmt"
	"time"

	"doctor-service/auth/jwt"
	"doctor-service/auth/otp"
	"doctor-service/auth/password"
	"doctor-service/auth/token"
	"doctor-service/config"
	"doctor-service/dto"
	"doctor-service/entities"
	"doctor-service/repositories"
	"doctor-service/sms"

	"github.com/google/uuid"
)

type AuthService interface {
	Register(ctx context.Context, req dto.RegisterRequest) (*dto.RegisterResponse, error)
	VerifyOTP(ctx context.Context, req dto.VerifyOTPRequest) (*dto.AuthResponse, error)
	Login(ctx context.Context, req dto.LoginRequest) (*dto.AuthResponse, error)
}

type DefaultAuthService struct {
	doctorRepo       repositories.DoctorRepository
	otpRepo          repositories.OTPRepository
	refreshTokenRepo repositories.RefreshTokenRepository
	smsProvider      sms.SMSProvider
	jwtManager       *jwt.JWTManager
	refreshTokenMgr  *token.RefreshTokenManager
	cfg              *config.Config
}

func NewAuthService(
	doctorRepo repositories.DoctorRepository,
	otpRepo repositories.OTPRepository,
	refreshTokenRepo repositories.RefreshTokenRepository,
	smsProvider sms.SMSProvider,
	jwtManager *jwt.JWTManager,
	refreshTokenMgr *token.RefreshTokenManager,
	cfg *config.Config,
) AuthService {
	return &DefaultAuthService{
		doctorRepo:       doctorRepo,
		otpRepo:          otpRepo,
		refreshTokenRepo: refreshTokenRepo,
		smsProvider:      smsProvider,
		jwtManager:       jwtManager,
		refreshTokenMgr:  refreshTokenMgr,
		cfg:              cfg,
	}
}

func (s *DefaultAuthService) Register(ctx context.Context, req dto.RegisterRequest) (*dto.RegisterResponse, error) {
	// 1. Password policy validation
	if err := password.ValidatePasswordPolicy(req.Password); err != nil {
		return nil, err
	}

	// 2. Check duplicate email
	existingEmail, err := s.doctorRepo.FindByEmail(ctx, req.Email)
	if err != nil {
		return nil, err
	}
	if existingEmail != nil {
		return nil, errors.New("email address is already registered")
	}

	// 3. Check duplicate mobile
	existingMobile, err := s.doctorRepo.FindByMobile(ctx, req.Mobile)
	if err != nil {
		return nil, err
	}
	if existingMobile != nil {
		return nil, errors.New("mobile number is already registered")
	}

	// 4. Hash password
	pwdHash, err := password.HashPassword(req.Password)
	if err != nil {
		return nil, fmt.Errorf("failed to hash password: %w", err)
	}

	// 5. Parse DOB if provided
	var dob *time.Time
	if req.DOB != "" {
		parsedDOB, err := time.Parse("2006-01-02", req.DOB)
		if err == nil {
			dob = &parsedDOB
		}
	}

	// 6. Create Doctor Entity
	doc := &entities.Doctor{
		FirstName:      req.FirstName,
		LastName:       req.LastName,
		Gender:         req.Gender,
		DOB:            dob,
		Mobile:         req.Mobile,
		Email:          req.Email,
		PasswordHash:   pwdHash,
		Status:         entities.DoctorStatusNotSubmitted,
		MobileVerified: false,
		EmailVerified:  false,
	}

	if err := s.doctorRepo.Create(ctx, doc); err != nil {
		return nil, fmt.Errorf("failed to create doctor record: %w", err)
	}

	// 7. Generate & Send OTP
	rawOTP, err := otp.GenerateSecureOTP(6)
	if err != nil {
		return nil, fmt.Errorf("failed to generate OTP: %w", err)
	}

	otpHash := otp.HashOTP(rawOTP)
	expiresAt := time.Now().Add(s.cfg.OTPDuration)

	otpEntity := &entities.OTPVerification{
		DoctorID:     doc.ID,
		Purpose:      entities.OTPPurposeRegister,
		OTP_Hash:     otpHash,
		ExpiresAt:    expiresAt,
		AttemptCount: 0,
		MaxAttempts:  s.cfg.OTPMaxAttempts,
	}

	if err := s.otpRepo.Create(ctx, otpEntity); err != nil {
		return nil, fmt.Errorf("failed to save OTP: %w", err)
	}

	// 8. Send SMS via provider
	_ = s.smsProvider.SendOTP(ctx, sms.SMSPayload{
		Mobile:  doc.Mobile,
		OTP:     rawOTP,
		Purpose: string(entities.OTPPurposeRegister),
	})

	return &dto.RegisterResponse{
		Message:          "Doctor registered successfully. OTP sent for mobile verification.",
		PublicID:         doc.PublicID,
		Mobile:           doc.Mobile,
		ExpiresInSeconds: int(s.cfg.OTPDuration.Seconds()),
	}, nil
}

func (s *DefaultAuthService) VerifyOTP(ctx context.Context, req dto.VerifyOTPRequest) (*dto.AuthResponse, error) {
	var doc *entities.Doctor
	var err error

	if req.PublicID != "" {
		pubUUID, parseErr := uuid.Parse(req.PublicID)
		if parseErr == nil {
			doc, err = s.doctorRepo.FindByPublicID(ctx, pubUUID)
		}
	} else if req.Mobile != "" {
		doc, err = s.doctorRepo.FindByMobile(ctx, req.Mobile)
	}

	if err != nil || doc == nil {
		return nil, errors.New("doctor account not found")
	}

	purpose := entities.OTPPurpose(req.Purpose)
	if purpose == "" {
		purpose = entities.OTPPurposeRegister
	}

	// 1. Fetch latest active OTP
	activeOTP, err := s.otpRepo.FindLatestActive(ctx, doc.ID, purpose)
	if err != nil || activeOTP == nil {
		return nil, errors.New("no active OTP verification process found")
	}

	// 2. Check Expiry
	if time.Now().After(activeOTP.ExpiresAt) {
		return nil, errors.New("OTP has expired. Please request a new OTP")
	}

	// 3. Check Max Attempts
	if activeOTP.AttemptCount >= activeOTP.MaxAttempts {
		return nil, errors.New("maximum OTP verification attempts exceeded. Please request a new OTP")
	}

	// 4. Validate OTP Hash
	if !otp.VerifyOTP(req.OTP, activeOTP.OTP_Hash) {
		_ = s.otpRepo.IncrementAttempt(ctx, activeOTP.ID)
		remaining := activeOTP.MaxAttempts - (activeOTP.AttemptCount + 1)
		return nil, fmt.Errorf("invalid OTP. %d attempts remaining", remaining)
	}

	// 5. Success - Mark OTP Verified & Mobile Verified
	if err := s.otpRepo.MarkVerified(ctx, activeOTP.ID); err != nil {
		return nil, err
	}

	if err := s.doctorRepo.MarkMobileVerified(ctx, doc.ID); err != nil {
		return nil, err
	}

	doc.MobileVerified = true

	// 6. Issue JWT & Refresh Tokens
	accessToken, accessExpiresAt, err := s.jwtManager.GenerateToken(doc.ID, doc.PublicID, doc.Email, "DOCTOR")
	if err != nil {
		return nil, fmt.Errorf("failed to generate access token: %w", err)
	}

	rawRefreshToken, refreshHash, refreshExpiresAt, err := s.refreshTokenMgr.GenerateRefreshToken()
	if err != nil {
		return nil, fmt.Errorf("failed to generate refresh token: %w", err)
	}

	refreshTokenEntity := &entities.RefreshToken{
		DoctorID:  doc.ID,
		TokenHash: refreshHash,
		ExpiresAt: refreshExpiresAt,
		IsRevoked: false,
	}

	if err := s.refreshTokenRepo.Create(ctx, refreshTokenEntity); err != nil {
		return nil, fmt.Errorf("failed to store refresh token: %w", err)
	}

	return &dto.AuthResponse{
		Message:        "Mobile number verified successfully.",
		AccessToken:    accessToken,
		RefreshToken:   rawRefreshToken,
		TokenType:      "Bearer",
		ExpiresIn:      int64(time.Until(accessExpiresAt).Seconds()),
		MobileVerified: true,
		Doctor: &dto.DoctorProfileDTO{
			PublicID:       doc.PublicID,
			FirstName:      doc.FirstName,
			LastName:       doc.LastName,
			Email:          doc.Email,
			Mobile:         doc.Mobile,
			Status:         string(doc.Status),
			MobileVerified: true,
			EmailVerified:  doc.EmailVerified,
		},
	}, nil
}

func (s *DefaultAuthService) Login(ctx context.Context, req dto.LoginRequest) (*dto.AuthResponse, error) {
	// 1. Find Doctor by Identifier (Email or Mobile)
	doc, err := s.doctorRepo.FindByIdentifier(ctx, req.Identifier)
	if err != nil || doc == nil {
		return nil, errors.New("invalid credentials")
	}

	// 2. Check if Suspended
	if doc.Status == entities.DoctorStatusSuspended {
		return nil, errors.New("account has been suspended. Please contact support")
	}

	// 3. Check Account Lockout
	if doc.AccountLockedUntil != nil && time.Now().Before(*doc.AccountLockedUntil) {
		lockRemaining := time.Until(*doc.AccountLockedUntil).Round(time.Second)
		return nil, fmt.Errorf("account is locked due to multiple failed login attempts. Try again in %v", lockRemaining)
	}

	// 4. Check Password
	if !password.CheckPasswordHash(req.Password, doc.PasswordHash) {
		failedCount, isLocked, err := s.doctorRepo.IncrementFailedLogin(ctx, doc.ID, s.cfg.MaxLoginAttempts, s.cfg.AccountLockDuration)
		if err != nil {
			return nil, errors.New("invalid credentials")
		}
		if isLocked {
			return nil, fmt.Errorf("account locked due to %d consecutive failed login attempts. Try again in %v", failedCount, s.cfg.AccountLockDuration)
		}
		return nil, errors.New("invalid credentials")
	}

	// 5. Password Match - Reset Failed Attempts
	_ = s.doctorRepo.ResetFailedLogin(ctx, doc.ID)

	// 6. Check Mobile Verification
	if !doc.MobileVerified {
		// Auto-generate new OTP for mobile verification
		rawOTP, err := otp.GenerateSecureOTP(6)
		if err == nil {
			otpHash := otp.HashOTP(rawOTP)
			_ = s.otpRepo.InvalidatePreviousOTPs(ctx, doc.ID, entities.OTPPurposeRegister)
			_ = s.otpRepo.Create(ctx, &entities.OTPVerification{
				DoctorID:     doc.ID,
				Purpose:      entities.OTPPurposeRegister,
				OTP_Hash:     otpHash,
				ExpiresAt:    time.Now().Add(s.cfg.OTPDuration),
				AttemptCount: 0,
				MaxAttempts:  s.cfg.OTPMaxAttempts,
			})
			_ = s.smsProvider.SendOTP(ctx, sms.SMSPayload{
				Mobile:  doc.Mobile,
				OTP:     rawOTP,
				Purpose: string(entities.OTPPurposeRegister),
			})
		}

		return &dto.AuthResponse{
			Message:        "Mobile verification pending. A fresh OTP has been sent to your mobile number.",
			MobileVerified: false,
			Doctor: &dto.DoctorProfileDTO{
				PublicID:       doc.PublicID,
				FirstName:      doc.FirstName,
				LastName:       doc.LastName,
				Email:          doc.Email,
				Mobile:         doc.Mobile,
				Status:         string(doc.Status),
				MobileVerified: false,
				EmailVerified:  doc.EmailVerified,
			},
		}, nil
	}

	// 7. Generate Tokens
	accessToken, accessExpiresAt, err := s.jwtManager.GenerateToken(doc.ID, doc.PublicID, doc.Email, "DOCTOR")
	if err != nil {
		return nil, fmt.Errorf("failed to generate access token: %w", err)
	}

	rawRefreshToken, refreshHash, refreshExpiresAt, err := s.refreshTokenMgr.GenerateRefreshToken()
	if err != nil {
		return nil, fmt.Errorf("failed to generate refresh token: %w", err)
	}

	refreshTokenEntity := &entities.RefreshToken{
		DoctorID:  doc.ID,
		TokenHash: refreshHash,
		ExpiresAt: refreshExpiresAt,
		IsRevoked: false,
	}

	_ = s.refreshTokenRepo.Create(ctx, refreshTokenEntity)

	return &dto.AuthResponse{
		Message:        "Login successful.",
		AccessToken:    accessToken,
		RefreshToken:   rawRefreshToken,
		TokenType:      "Bearer",
		ExpiresIn:      int64(time.Until(accessExpiresAt).Seconds()),
		MobileVerified: true,
		Doctor: &dto.DoctorProfileDTO{
			PublicID:       doc.PublicID,
			FirstName:      doc.FirstName,
			LastName:       doc.LastName,
			Email:          doc.Email,
			Mobile:         doc.Mobile,
			Status:         string(doc.Status),
			MobileVerified: true,
			EmailVerified:  doc.EmailVerified,
		},
	}, nil
}
