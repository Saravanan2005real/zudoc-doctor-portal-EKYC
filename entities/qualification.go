package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type DoctorQualification struct {
	QualificationID uuid.UUID      `gorm:"primaryKey" json:"qualification_id"`
	DoctorID        uuid.UUID      `gorm:"not null;index" json:"doctor_id"`
	Degree          string         `gorm:"size:100;not null" json:"degree"`
	Specialization  string         `gorm:"size:255" json:"specialization,omitempty"`
	College         string         `gorm:"size:255;not null" json:"college"`
	University      string         `gorm:"size:255;not null" json:"university"`
	YearCompleted   int            `gorm:"not null" json:"year_completed"`
	CreatedAt       time.Time      `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt       time.Time      `gorm:"autoUpdateTime" json:"updated_at"`
	DeletedAt       gorm.DeletedAt `gorm:"index" json:"-"`
}

func (q *DoctorQualification) BeforeCreate(tx *gorm.DB) (err error) {
	if q.QualificationID == uuid.Nil {
		q.QualificationID = uuid.New()
	}
	return nil
}
