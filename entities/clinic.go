package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type ConsultationMode string

const (
	ConsultationModeInPerson ConsultationMode = "IN_PERSON"
	ConsultationModeOffline  ConsultationMode = "IN_PERSON"
	ConsultationModeVideo    ConsultationMode = "VIDEO"
	ConsultationModeBoth     ConsultationMode = "BOTH"
)

type DoctorClinic struct {
	ClinicID         uuid.UUID        `gorm:"primaryKey" json:"clinic_id"`
	DoctorID         uuid.UUID        `gorm:"not null;index" json:"doctor_id"`
	ClinicName       string           `gorm:"size:255;not null" json:"clinic_name"`
	Address          string           `gorm:"type:text;not null" json:"address"`
	City             string           `gorm:"size:100;not null;index" json:"city"`
	State            string           `gorm:"size:100;not null" json:"state"`
	Pincode          string           `gorm:"size:20;not null" json:"pincode"`
	Latitude         *float64         `json:"latitude,omitempty"`
	Longitude        *float64         `json:"longitude,omitempty"`
	ConsultationMode ConsultationMode `gorm:"size:50;default:'IN_PERSON';not null" json:"consultation_mode"`
	ConsultationFee  float64          `gorm:"type:decimal(10,2);not null" json:"consultation_fee"`
	CreatedAt        time.Time        `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt        time.Time        `gorm:"autoUpdateTime" json:"updated_at"`
	DeletedAt        gorm.DeletedAt   `gorm:"index" json:"-"`
}

func (c *DoctorClinic) BeforeCreate(tx *gorm.DB) (err error) {
	if c.ClinicID == uuid.Nil {
		c.ClinicID = uuid.New()
	}
	return nil
}
