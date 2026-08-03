package dto

import (
	"github.com/google/uuid"
)

type RegisterRequest struct {
	FirstName string `json:"first_name" binding:"required"`
	LastName  string `json:"last_name" binding:"required"`
	Gender    string `json:"gender"`
	DOB       string `json:"dob"` // YYYY-MM-DD
	Mobile    string `json:"mobile" binding:"required"`
	Email     string `json:"email" binding:"required,email"`
	Password  string `json:"password" binding:"required"`
}

type RegisterResponse struct {
	Message          string    `json:"message"`
	PublicID         uuid.UUID `json:"public_id"`
	Mobile           string    `json:"mobile"`
	ExpiresInSeconds int       `json:"expires_in_seconds"`
}

type VerifyOTPRequest struct {
	PublicID string `json:"public_id"`
	Mobile   string `json:"mobile"`
	OTP      string `json:"otp" binding:"required"`
	Purpose  string `json:"purpose" binding:"required"`
}

type LoginRequest struct {
	Identifier string `json:"identifier" binding:"required"` // Mobile or Email
	Password   string `json:"password" binding:"required"`
}

type DoctorProfileDTO struct {
	PublicID       uuid.UUID `json:"public_id"`
	FirstName      string    `json:"first_name"`
	LastName       string    `json:"last_name"`
	Email          string    `json:"email"`
	Mobile         string    `json:"mobile"`
	Status         string    `json:"status"`
	MobileVerified bool      `json:"mobile_verified"`
	EmailVerified  bool      `json:"email_verified"`
}

type AuthResponse struct {
	Message        string            `json:"message"`
	AccessToken    string            `json:"access_token,omitempty"`
	RefreshToken   string            `json:"refresh_token,omitempty"`
	TokenType      string            `json:"token_type,omitempty"`
	ExpiresIn      int64             `json:"expires_in,omitempty"`
	MobileVerified bool              `json:"mobile_verified"`
	Doctor         *DoctorProfileDTO `json:"doctor,omitempty"`
}
