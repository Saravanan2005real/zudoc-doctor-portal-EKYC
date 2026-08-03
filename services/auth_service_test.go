package services_test

import (
	"testing"
	"time"

	"doctor-service/auth/jwt"
	"doctor-service/auth/otp"
	"doctor-service/auth/password"
	"doctor-service/auth/token"

	"github.com/google/uuid"
)

func TestPasswordPolicyValidation(t *testing.T) {
	tests := []struct {
		password string
		valid    bool
	}{
		{"short1!", false},
		{"nopunctuation123", false},
		{"NO_LOWERCASE_123!", false},
		{"no_uppercase_123!", false},
		{"NoDigitsHere!@#", false},
		{"ValidP@ssw0rd2026", true},
	}

	for _, tt := range tests {
		err := password.ValidatePasswordPolicy(tt.password)
		if tt.valid && err != nil {
			t.Errorf("expected password '%s' to be valid, got: %v", tt.password, err)
		}
		if !tt.valid && err == nil {
			t.Errorf("expected password '%s' to be invalid, but passed", tt.password)
		}
	}
}

func TestOTPGenerationAndVerification(t *testing.T) {
	otpVal, err := otp.GenerateSecureOTP(6)
	if err != nil {
		t.Fatalf("failed to generate OTP: %v", err)
	}

	if len(otpVal) != 6 {
		t.Fatalf("expected 6-digit OTP, got length %d (%s)", len(otpVal), otpVal)
	}

	hash := otp.HashOTP(otpVal)
	if !otp.VerifyOTP(otpVal, hash) {
		t.Fatalf("OTP verification failed for matching OTP")
	}

	if otp.VerifyOTP("000000", hash) && otpVal != "000000" {
		t.Fatalf("OTP verification succeeded for wrong OTP")
	}
}

func TestJWTGenerationAndValidation(t *testing.T) {
	jwtMgr := jwt.NewJWTManager("test-secret-key-12345", 15*time.Minute)
	doctorID := uuid.New()
	publicID := uuid.New()

	tokenStr, expiresAt, err := jwtMgr.GenerateToken(doctorID, publicID, "doctor@example.com", "DOCTOR")
	if err != nil {
		t.Fatalf("failed to generate JWT: %v", err)
	}

	if tokenStr == "" || expiresAt.Before(time.Now()) {
		t.Fatalf("invalid token string or expiration")
	}

	claims, err := jwtMgr.ValidateToken(tokenStr)
	if err != nil {
		t.Fatalf("failed to validate JWT: %v", err)
	}

	if claims.DoctorID != doctorID || claims.PublicID != publicID || claims.Email != "doctor@example.com" {
		t.Fatalf("JWT claims mismatch")
	}
}

func TestRefreshTokenManager(t *testing.T) {
	rfMgr := token.NewRefreshTokenManager(30 * 24 * time.Hour)
	rawToken, tokenHash, expiresAt, err := rfMgr.GenerateRefreshToken()

	if err != nil {
		t.Fatalf("failed to generate refresh token: %v", err)
	}

	if rawToken == "" || tokenHash == "" || expiresAt.Before(time.Now()) {
		t.Fatalf("invalid refresh token parameters")
	}

	if token.HashRefreshToken(rawToken) != tokenHash {
		t.Fatalf("refresh token hash mismatch")
	}
}
