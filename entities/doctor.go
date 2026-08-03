package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type DoctorStatus string

const (
	DoctorStatusNotSubmitted       DoctorStatus = "NOT_SUBMITTED"
	DoctorStatusPending            DoctorStatus = "PENDING"
	DoctorStatusAutoVerified       DoctorStatus = "AUTO_VERIFIED"
	DoctorStatusManualReview       DoctorStatus = "MANUAL_REVIEW"
	DoctorStatusVerified           DoctorStatus = "VERIFIED"
	DoctorStatusRejected           DoctorStatus = "REJECTED"
	DoctorStatusSuspended          DoctorStatus = "SUSPENDED"
	DoctorStatusDocumentsRequested DoctorStatus = "DOCUMENTS_REQUESTED"
)

type Doctor struct {
	ID                  uuid.UUID      `gorm:"primaryKey" json:"id"`
	PublicID            uuid.UUID      `gorm:"uniqueIndex;not null" json:"public_id"`
	FirstName           string         `gorm:"size:100;not null" json:"first_name"`
	LastName            string         `gorm:"size:100;not null" json:"last_name"`
	Gender              string         `gorm:"size:20" json:"gender"`
	DOB                 *time.Time     `json:"dob"`
	Mobile              string         `gorm:"size:20;uniqueIndex;not null" json:"mobile"`
	Email               string         `gorm:"size:255;uniqueIndex;not null" json:"email"`
	PasswordHash        string         `gorm:"size:255;not null" json:"-"`
	ProfilePhoto        string         `gorm:"type:text" json:"profile_photo,omitempty"`
	Languages           string         `gorm:"size:255" json:"languages,omitempty"`
	Biography           string         `gorm:"type:text" json:"biography,omitempty"`
	Status              DoctorStatus   `gorm:"size:50;default:'NOT_SUBMITTED';not null;index" json:"status"`
	FraudScore          int            `gorm:"default:0" json:"fraud_score"`
	MobileVerified      bool           `gorm:"default:false;not null" json:"mobile_verified"`
	EmailVerified       bool           `gorm:"default:false;not null" json:"email_verified"`
	LastLoginAt         *time.Time     `json:"last_login_at,omitempty"`
	FailedLoginAttempts int            `gorm:"default:0;not null" json:"failed_login_attempts"`
	AccountLockedUntil  *time.Time     `json:"account_locked_until,omitempty"`
	PasswordChangedAt   *time.Time     `json:"password_changed_at,omitempty"`
	AssignedAdminID     *uuid.UUID     `json:"assigned_admin_id,omitempty"`
	AssignedAt          *time.Time     `json:"assigned_at,omitempty"`
	PrescriptionEnabled bool           `gorm:"default:false;not null" json:"prescription_enabled"`
	CreatedAt           time.Time      `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt           time.Time      `gorm:"autoUpdateTime" json:"updated_at"`
	DeletedAt           gorm.DeletedAt `gorm:"index" json:"-"`
	DeletedBy           *uuid.UUID     `json:"deleted_by,omitempty"`

	// Relationships
	Licenses       []DoctorLicense       `gorm:"foreignKey:DoctorID;constraint:OnDelete:CASCADE" json:"licenses,omitempty"`
	Qualifications []DoctorQualification `gorm:"foreignKey:DoctorID;constraint:OnDelete:CASCADE" json:"qualifications,omitempty"`
	Clinics        []DoctorClinic        `gorm:"foreignKey:DoctorID;constraint:OnDelete:CASCADE" json:"clinics,omitempty"`
	Documents      []DoctorDocument      `gorm:"foreignKey:DoctorID;constraint:OnDelete:CASCADE" json:"documents,omitempty"`
	Histories      []VerificationHistory `gorm:"foreignKey:DoctorID;constraint:OnDelete:CASCADE" json:"histories,omitempty"`
	OTPs           []OTPVerification     `gorm:"foreignKey:DoctorID;constraint:OnDelete:CASCADE" json:"-"`
	RefreshTokens  []RefreshToken        `gorm:"foreignKey:DoctorID;constraint:OnDelete:CASCADE" json:"-"`
	Notes          []DoctorNote          `gorm:"foreignKey:DoctorID;constraint:OnDelete:CASCADE" json:"notes,omitempty"`
	Flags          []VerificationFlag    `gorm:"foreignKey:DoctorID;constraint:OnDelete:CASCADE" json:"flags,omitempty"`
	AdminActions   []AdminAction         `gorm:"foreignKey:DoctorID;constraint:OnDelete:CASCADE" json:"admin_actions,omitempty"`
}

func (d *Doctor) BeforeCreate(tx *gorm.DB) (err error) {
	if d.ID == uuid.Nil {
		d.ID = uuid.New()
	}
	if d.PublicID == uuid.Nil {
		d.PublicID = uuid.New()
	}
	return nil
}
