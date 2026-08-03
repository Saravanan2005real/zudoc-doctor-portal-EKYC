package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type DocumentOCRResult struct {
	ID               uuid.UUID `gorm:"primaryKey" json:"id"`
	DocumentID       uuid.UUID `gorm:"not null;index" json:"document_id"`
	Provider         string    `gorm:"size:50;not null" json:"provider"`
	RawJSON          string    `gorm:"type:text;not null" json:"raw_json"`
	ParsedJSON       string    `gorm:"type:text;not null" json:"parsed_json"`
	Confidence       float64   `gorm:"not null" json:"confidence"`
	ProcessingTimeMS int64     `gorm:"not null" json:"processing_time_ms"`
	CreatedAt        time.Time `gorm:"autoCreateTime" json:"created_at"`
}

func (o *DocumentOCRResult) BeforeCreate(tx *gorm.DB) (err error) {
	if o.ID == uuid.Nil {
		o.ID = uuid.New()
	}
	return nil
}
