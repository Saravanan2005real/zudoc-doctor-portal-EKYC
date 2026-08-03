package council

import (
	"context"
)

type CouncilVerificationResult struct {
	IsVerified          bool   `json:"is_verified"`
	DoctorName          string `json:"doctor_name"`
	RegistrationNumber  string `json:"registration_number"`
	CouncilName         string `json:"council_name"`
	RegistrationYear    int    `json:"registration_year"`
	Status              string `json:"status"` // "ACTIVE", "SUSPENDED", "NOT_FOUND", "MANUAL_REVIEW_REQUIRED"
	VerificationSource  string `json:"verification_source"`
	Remarks             string `json:"remarks,omitempty"`
}

type CouncilVerificationProvider interface {
	Verify(ctx context.Context, registrationNumber string, council string) (*CouncilVerificationResult, error)
	GetProviderName() string
}
