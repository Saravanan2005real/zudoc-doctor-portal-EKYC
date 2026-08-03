package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type OTPPurpose string

const (
	OTPPurposeRegister       OTPPurpose = "REGISTER"
	OTPPurposeLogin          OTPPurpose = "LOGIN"
	OTPPurposePasswordReset OTPPurpose = "PASSWORD_RESET"
)

type OTPVerification struct {
	ID           uuid.UUID  `gorm:"primaryKey" json:"id"`
	DoctorID     uuid.UUID  `gorm:"not null;index" json:"doctor_id"`
	Purpose      OTPPurpose `gorm:"size:50;not null" json:"purpose"`
	OTP_Hash     string     `gorm:"size:255;not null" json:"-"`
	ExpiresAt    time.Time  `gorm:"not null;index" json:"expires_at"`
	IsVerified   bool       `gorm:"default:false;not null" json:"is_verified"`
	AttemptCount int        `gorm:"default:0;not null" json:"attempt_count"`
	MaxAttempts  int        `gorm:"default:5;not null" json:"max_attempts"`
	CreatedAt    time.Time  `gorm:"autoCreateTime" json:"created_at"`
}

func (o *OTPVerification) BeforeCreate(tx *gorm.DB) (err error) {
	if o.ID == uuid.Nil {
		o.ID = uuid.New()
	}
	return nil
}
