package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type JobStatus string
type JobType string

const (
	JobStatusQueued     JobStatus = "QUEUED"
	JobStatusProcessing JobStatus = "PROCESSING"
	JobStatusRunning    JobStatus = "PROCESSING"
	JobStatusCompleted  JobStatus = "COMPLETED"
	JobStatusSuccess    JobStatus = "COMPLETED"
	JobStatusFailed     JobStatus = "FAILED"

	JobTypeFullPipeline JobType = "FULL_PIPELINE"
	JobTypeOCROnly      JobType = "OCR_ONLY"
	JobTypeOCR          JobType = "OCR_ONLY"
	JobTypeCouncilOnly  JobType = "COUNCIL_ONLY"
)

type VerificationJob struct {
	JobID        uuid.UUID  `gorm:"primaryKey" json:"job_id"`
	DoctorID     uuid.UUID  `gorm:"not null;index" json:"doctor_id"`
	JobType      JobType    `gorm:"size:50;default:'FULL_PIPELINE';not null" json:"job_type"`
	Status       JobStatus  `gorm:"size:50;default:'QUEUED';not null;index" json:"status"`
	Priority     int        `gorm:"default:1;not null;index" json:"priority"`
	RetryCount   int        `gorm:"default:0;not null" json:"retry_count"`
	MaxRetries   int        `gorm:"default:3;not null" json:"max_retries"`
	ErrorMessage *string    `gorm:"type:text" json:"error_message,omitempty"`
	StartedAt    *time.Time `json:"started_at,omitempty"`
	CompletedAt  *time.Time `json:"completed_at,omitempty"`
	CreatedAt    time.Time  `gorm:"autoCreateTime;index" json:"created_at"`
	UpdatedAt    time.Time  `gorm:"autoUpdateTime" json:"updated_at"`
}

func (j *VerificationJob) BeforeCreate(tx *gorm.DB) (err error) {
	if j.JobID == uuid.Nil {
		j.JobID = uuid.New()
	}
	return nil
}
