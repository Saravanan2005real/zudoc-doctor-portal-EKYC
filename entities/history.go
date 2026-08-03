package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type VerificationHistory struct {
	ID          uuid.UUID  `gorm:"primaryKey" json:"id"`
	DoctorID    uuid.UUID  `gorm:"not null;index" json:"doctor_id"`
	Action      string     `gorm:"size:100;not null" json:"action"`
	Status      string     `gorm:"size:50;not null" json:"status"`
	Remarks     *string    `gorm:"type:text" json:"remarks,omitempty"`
	PerformedBy *uuid.UUID `json:"performed_by,omitempty"`
	PerformedAt time.Time  `gorm:"autoCreateTime" json:"performed_at"`
}

func (h *VerificationHistory) BeforeCreate(tx *gorm.DB) (err error) {
	if h.ID == uuid.Nil {
		h.ID = uuid.New()
	}
	return nil
}
