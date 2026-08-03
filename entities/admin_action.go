package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type AdminAction struct {
	ID             uuid.UUID `gorm:"primaryKey" json:"id"`
	AdminID        uuid.UUID `gorm:"not null;index" json:"admin_id"`
	DoctorID       uuid.UUID `gorm:"not null;index" json:"doctor_id"`
	Action         string    `gorm:"size:50;not null" json:"action"`
	PreviousStatus string    `gorm:"size:50;not null" json:"previous_status"`
	NewStatus      string    `gorm:"size:50;not null" json:"new_status"`
	Reason         *string   `gorm:"type:text" json:"reason,omitempty"`
	IPAddress      *string   `gorm:"size:50" json:"ip_address,omitempty"`
	UserAgent      *string   `gorm:"type:text" json:"user_agent,omitempty"`
	CreatedAt      time.Time `gorm:"autoCreateTime" json:"created_at"`
}

func (a *AdminAction) BeforeCreate(tx *gorm.DB) (err error) {
	if a.ID == uuid.Nil {
		a.ID = uuid.New()
	}
	return nil
}
