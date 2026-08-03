package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type AuditEvent struct {
	EventID      uuid.UUID `gorm:"primaryKey" json:"event_id"`
	ActorType    string    `gorm:"size:50;not null;index" json:"actor_type"`
	ActorID      uuid.UUID `gorm:"not null;index" json:"actor_id"`
	Action       string    `gorm:"size:100;not null;index" json:"action"`
	ResourceType string    `gorm:"size:100;not null" json:"resource_type"`
	ResourceID   string    `gorm:"size:255;not null" json:"resource_id"`
	BeforeState  *string   `gorm:"type:text" json:"before_state,omitempty"`
	AfterState   *string   `gorm:"type:text" json:"after_state,omitempty"`
	IPAddress    *string   `gorm:"size:50" json:"ip_address,omitempty"`
	Device       *string   `gorm:"type:text" json:"device,omitempty"`
	Timestamp    time.Time `gorm:"autoCreateTime" json:"timestamp"`
}

func (a *AuditEvent) BeforeCreate(tx *gorm.DB) (err error) {
	if a.EventID == uuid.Nil {
		a.EventID = uuid.New()
	}
	return nil
}
