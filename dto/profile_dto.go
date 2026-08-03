package dto

import (
	"time"

	"github.com/google/uuid"
)

type UpdateProfileRequest struct {
	DOB          string `json:"dob"` // YYYY-MM-DD
	Gender       string `json:"gender"`
	ProfilePhoto string `json:"profile_photo"`
	Languages    string `json:"languages"`
	Biography    string `json:"biography"`
}

type AddLicenseRequest struct {
	RegistrationNumber  string `json:"registration_number" binding:"required"`
	RegistrationCouncil string `json:"registration_council" binding:"required"`
	RegistrationYear    int    `json:"registration_year" binding:"required"`
	IssueDate           string `json:"issue_date"`
	ExpiryDate          string `json:"expiry_date"`
}

type LicenseResponse struct {
	LicenseID           uuid.UUID `json:"license_id"`
	RegistrationNumber  string    `json:"registration_number"`
	RegistrationCouncil string    `json:"registration_council"`
	RegistrationYear    int       `json:"registration_year"`
	LicenseStatus       string    `json:"license_status"`
	VerificationStatus  string    `json:"verification_status"`
	CreatedAt           time.Time `json:"created_at"`
}

type AddQualificationRequest struct {
	Degree         string `json:"degree" binding:"required"` // MBBS, MD, MS, DM, DNB
	Specialization string `json:"specialization"`
	College        string `json:"college" binding:"required"`
	University     string `json:"university" binding:"required"`
	YearCompleted  int    `json:"year_completed" binding:"required"`
}

type QualificationResponse struct {
	QualificationID uuid.UUID `json:"qualification_id"`
	Degree          string    `json:"degree"`
	Specialization  string    `json:"specialization"`
	College         string    `json:"college"`
	University      string    `json:"university"`
	YearCompleted   int       `json:"year_completed"`
	CreatedAt       time.Time `json:"created_at"`
}

type AddClinicRequest struct {
	ClinicName       string   `json:"clinic_name" binding:"required"`
	Address          string   `json:"address" binding:"required"`
	City             string   `json:"city" binding:"required"`
	State            string   `json:"state" binding:"required"`
	Pincode          string   `json:"pincode" binding:"required"`
	Latitude         *float64 `json:"latitude"`
	Longitude        *float64 `json:"longitude"`
	ConsultationMode string   `json:"consultation_mode" binding:"required"` // ONLINE, OFFLINE, BOTH
	ConsultationFee  float64  `json:"consultation_fee"`
}

type ClinicResponse struct {
	ClinicID         uuid.UUID `json:"clinic_id"`
	ClinicName       string    `json:"clinic_name"`
	Address          string    `json:"address"`
	City             string    `json:"city"`
	State            string    `json:"state"`
	Pincode          string    `json:"pincode"`
	ConsultationMode string    `json:"consultation_mode"`
	ConsultationFee  float64   `json:"consultation_fee"`
	CreatedAt        time.Time `json:"created_at"`
}

type DocumentUploadResponse struct {
	DocumentID       uuid.UUID `json:"document_id"`
	DoctorID         uuid.UUID `json:"doctor_id"`
	DocumentType     string    `json:"document_type"`
	FileURL          string    `json:"file_url"`
	OriginalFilename string    `json:"original_filename"`
	MIMEType         string    `json:"mime_type"`
	FileSize         int64     `json:"file_size"`
	FileHash         string    `json:"file_hash"`
	Version          int       `json:"version"`
	IsLatest         bool      `json:"is_latest"`
	OCRStatus        string    `json:"ocr_status"`
	UploadedAt       time.Time `json:"uploaded_at"`
}

type SubmitVerificationResponse struct {
	Message     string    `json:"message"`
	PublicID    uuid.UUID `json:"public_id"`
	Status      string    `json:"status"`
	SubmittedAt time.Time `json:"submitted_at"`
}
