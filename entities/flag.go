package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type FlagSeverity string

const (
	FlagSeverityLow      FlagSeverity = "LOW"
	FlagSeverityMedium   FlagSeverity = "MEDIUM"
	FlagSeverityHigh     FlagSeverity = "HIGH"
	FlagSeverityCritical FlagSeverity = "CRITICAL"
)

type VerificationFlag struct {
	ID         uuid.UUID    `gorm:"primaryKey" json:"id"`
	DoctorID   uuid.UUID    `gorm:"not null;index" json:"doctor_id"`
	FlagType   string       `gorm:"size:100;not null" json:"flag_type"`
	Severity   FlagSeverity `gorm:"size:50;default:'MEDIUM';not null" json:"severity"`
	Message    string       `gorm:"type:text;not null" json:"message"`
	Resolved   bool         `gorm:"default:false;not null" json:"resolved"`
	ResolvedBy *uuid.UUID   `json:"resolved_by,omitempty"`
	ResolvedAt *time.Time   `json:"resolved_at,omitempty"`
	CreatedAt  time.Time    `gorm:"autoCreateTime" json:"created_at"`
}

func (f *VerificationFlag) BeforeCreate(tx *gorm.DB) (err error) {
	if f.ID == uuid.Nil {
		f.ID = uuid.New()
	}
	return nil
}
