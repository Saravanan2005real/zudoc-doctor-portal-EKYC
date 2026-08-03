package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type VerificationDeadJob struct {
	ID            uuid.UUID `gorm:"primaryKey" json:"id"`
	JobID         uuid.UUID `gorm:"not null" json:"job_id"`
	DoctorID      uuid.UUID `gorm:"not null;index" json:"doctor_id"`
	FailureReason string    `gorm:"type:text;not null" json:"failure_reason"`
	RetryCount    int       `gorm:"default:0;not null" json:"retry_count"`
	PayloadJSON   *string   `gorm:"type:text" json:"payload_json,omitempty"`
	FailedAt      time.Time `gorm:"autoCreateTime" json:"failed_at"`
}

func (d *VerificationDeadJob) BeforeCreate(tx *gorm.DB) (err error) {
	if d.ID == uuid.Nil {
		d.ID = uuid.New()
	}
	return nil
}
