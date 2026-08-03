package events

import (
	"time"

	"github.com/google/uuid"
)

type EventType string

const (
	EventTypeDoctorRegistered      EventType = "DoctorRegistered"
	EventTypeDocumentUploaded      EventType = "DocumentUploaded"
	EventTypeVerificationSubmitted EventType = "VerificationSubmitted"
	EventTypeOCRCompleted          EventType = "OCRCompleted"
	EventTypeDoctorVerified        EventType = "DoctorVerified"
	EventTypePrescriptionIssued    EventType = "PrescriptionIssued"
)

type Event interface {
	GetType() EventType
	GetDoctorID() uuid.UUID
	GetTimestamp() time.Time
}

type BaseEvent struct {
	Type      EventType `json:"type"`
	DoctorID  uuid.UUID `json:"doctor_id"`
	Timestamp time.Time `json:"timestamp"`
}

func (e BaseEvent) GetType() EventType       { return e.Type }
func (e BaseEvent) GetDoctorID() uuid.UUID  { return e.DoctorID }
func (e BaseEvent) GetTimestamp() time.Time { return e.Timestamp }

type DoctorRegisteredEvent struct {
	BaseEvent
	Email  string `json:"email"`
	Mobile string `json:"mobile"`
}

type DocumentUploadedEvent struct {
	BaseEvent
	DocumentID   uuid.UUID `json:"document_id"`
	DocumentType string    `json:"document_type"`
	FileURL      string    `json:"file_url"`
}

type VerificationSubmittedEvent struct {
	BaseEvent
	JobID uuid.UUID `json:"job_id"`
}

type OCRCompletedEvent struct {
	BaseEvent
	DocumentID uuid.UUID `json:"document_id"`
	Confidence float64   `json:"confidence"`
}

type DoctorVerifiedEvent struct {
	BaseEvent
	ApprovedBy uuid.UUID `json:"approved_by"`
}

type PrescriptionIssuedEvent struct {
	BaseEvent
	PrescriptionID uuid.UUID `json:"prescription_id"`
	PatientID      string    `json:"patient_id"`
}
