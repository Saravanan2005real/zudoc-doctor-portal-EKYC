package dto

import (
	"time"

	"doctor-service/entities"

	"github.com/google/uuid"
)

type AdminDoctorListItem struct {
	PublicID            uuid.UUID `json:"public_id"`
	DoctorName          string    `json:"doctor_name"`
	Email               string    `json:"email"`
	Mobile              string    `json:"mobile"`
	Status              string    `json:"status"`
	FraudScore          int       `json:"fraud_score"`
	RiskCategory        string    `json:"risk_category"`
	AssignedAdminID     *uuid.UUID `json:"assigned_admin_id,omitempty"`
	PrescriptionEnabled bool      `json:"prescription_enabled"`
	UnresolvedFlagsCount int       `json:"unresolved_flags_count"`
	CreatedAt           time.Time `json:"created_at"`
}

type AdminDashboardResponse struct {
	TotalDoctors int                   `json:"total_doctors"`
	Page         int                   `json:"page"`
	PageSize     int                   `json:"page_size"`
	TotalPages   int                   `json:"total_pages"`
	Doctors      []AdminDoctorListItem `json:"doctors"`
}

type SideBySideComparisonRow struct {
	Field          string  `json:"field"`
	DoctorEntered string  `json:"doctor_entered"`
	OCRExtracted   string  `json:"ocr_extracted"`
	MatchScore     float64 `json:"match_score"`
	IsMatch        bool    `json:"is_match"`
}

type DoctorVerificationDetailResponse struct {
	Profile              DoctorProfileDTO            `json:"profile"`
	AssignedAdminID      *uuid.UUID                  `json:"assigned_admin_id,omitempty"`
	AssignedAt           *time.Time                  `json:"assigned_at,omitempty"`
	PrescriptionEnabled  bool                        `json:"prescription_enabled"`
	Licenses             []LicenseResponse           `json:"licenses"`
	Qualifications       []QualificationResponse     `json:"qualifications"`
	Clinics              []ClinicResponse            `json:"clinics"`
	Documents            []DocumentUploadResponse    `json:"documents"`
	OCRResults           []entities.DocumentOCRResult `json:"ocr_results"`
	SideBySideComparison []SideBySideComparisonRow   `json:"side_by_side_comparison"`
	FraudScore           int                         `json:"fraud_score"`
	RiskCategory         string                      `json:"risk_category"`
	Flags                []entities.VerificationFlag `json:"flags"`
	Timeline             []entities.VerificationHistory `json:"timeline"`
	AdminActions         []entities.AdminAction      `json:"admin_actions"`
	Notes                []entities.DoctorNote       `json:"notes"`
}

type ApproveDoctorRequest struct {
	Reason string `json:"reason"`
}

type RejectDoctorRequest struct {
	Reason string `json:"reason" binding:"required"`
}

type RequestDocumentsRequest struct {
	RequiredDocuments []string `json:"required_documents" binding:"required"`
	Message           string   `json:"message" binding:"required"`
}

type AddNoteRequest struct {
	Note       string `json:"note" binding:"required"`
	Visibility string `json:"visibility"` // "INTERNAL", "VISIBLE_TO_DOCTOR"
}
