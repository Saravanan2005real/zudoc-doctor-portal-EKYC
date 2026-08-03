package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type Prescription struct {
	PrescriptionID   uuid.UUID `gorm:"primaryKey" json:"prescription_id"`
	DoctorID         uuid.UUID `gorm:"not null;index" json:"doctor_id"`
	PatientID        string    `gorm:"size:100;not null" json:"patient_id"`
	Diagnosis        string    `gorm:"type:text;not null" json:"diagnosis"`
	MedicinesJSON    string    `gorm:"type:text;not null" json:"medicines"`
	DigitalSignature string    `gorm:"type:text;not null" json:"digital_signature"`
	QRPayload        string    `gorm:"type:text;not null" json:"qr_payload"`
	IssuedAt         time.Time `gorm:"autoCreateTime" json:"issued_at"`
}

func (p *Prescription) BeforeCreate(tx *gorm.DB) (err error) {
	if p.PrescriptionID == uuid.Nil {
		p.PrescriptionID = uuid.New()
	}
	return nil
}
