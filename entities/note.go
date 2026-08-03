package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type NoteVisibility string

const (
	NoteVisibilityInternal        NoteVisibility = "INTERNAL"
	NoteVisibilityVisibleToDoctor NoteVisibility = "VISIBLE_TO_DOCTOR"
)

type DoctorNote struct {
	ID         uuid.UUID      `gorm:"primaryKey" json:"id"`
	DoctorID   uuid.UUID      `gorm:"not null;index" json:"doctor_id"`
	AdminID    uuid.UUID      `gorm:"not null;index" json:"admin_id"`
	Note       string         `gorm:"type:text;not null" json:"note"`
	Visibility NoteVisibility `gorm:"size:50;default:'INTERNAL';not null" json:"visibility"`
	CreatedAt  time.Time      `gorm:"autoCreateTime" json:"created_at"`
}

func (n *DoctorNote) BeforeCreate(tx *gorm.DB) (err error) {
	if n.ID == uuid.Nil {
		n.ID = uuid.New()
	}
	return nil
}
