package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type VerificationStatus string

const (
	VerificationStatusUnverified VerificationStatus = "UNVERIFIED"
	VerificationStatusPending    VerificationStatus = "PENDING"
	VerificationStatusVerified   VerificationStatus = "VERIFIED"
	VerificationStatusRejected   VerificationStatus = "REJECTED"
)

type DoctorLicense struct {
	LicenseID           uuid.UUID          `gorm:"primaryKey" json:"license_id"`
	DoctorID            uuid.UUID          `gorm:"not null;index" json:"doctor_id"`
	RegistrationNumber  string             `gorm:"size:100;not null;index" json:"registration_number"`
	RegistrationCouncil string             `gorm:"size:255;not null" json:"registration_council"`
	RegistrationYear    int                `gorm:"not null" json:"registration_year"`
	IssueDate           *time.Time         `json:"issue_date,omitempty"`
	ExpiryDate          *time.Time         `json:"expiry_date,omitempty"`
	LicenseStatus       string             `gorm:"size:50;default:'ACTIVE'" json:"license_status"`
	VerificationStatus  VerificationStatus `gorm:"size:50;default:'UNVERIFIED';not null" json:"verification_status"`
	CreatedAt           time.Time          `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt           time.Time          `gorm:"autoUpdateTime" json:"updated_at"`
	DeletedAt           gorm.DeletedAt     `gorm:"index" json:"-"`
}

func (l *DoctorLicense) BeforeCreate(tx *gorm.DB) (err error) {
	if l.LicenseID == uuid.Nil {
		l.LicenseID = uuid.New()
	}
	return nil
}
