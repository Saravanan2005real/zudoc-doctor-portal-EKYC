package ocr

import (
	"context"
	"io"

	"doctor-service/entities"
)

type ExtractedFields struct {
	DoctorName         string  `json:"doctor_name"`
	RegistrationNumber string  `json:"registration_number"`
	RegistrationCouncil string `json:"registration_council"`
	RegistrationYear   int     `json:"registration_year"`
	Degree             string  `json:"degree"`
	Specialization     string  `json:"specialization"`
	University         string  `json:"university"`
	College            string  `json:"college"`
	YearCompleted      int     `json:"year_completed"`
	DOB                string  `json:"dob"`
	GovtIDNumber       string  `json:"govt_id_number"`
}

type OCRResult struct {
	RawJSON          string
	ParsedFields     ExtractedFields
	Confidence       float64
	ProcessingTimeMS int64
}

type OCRProvider interface {
	Extract(ctx context.Context, doc *entities.DoctorDocument, fileReader io.Reader) (*OCRResult, error)
	GetProviderName() string
}
