package services

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"doctor-service/dto"
	"doctor-service/entities"
	"doctor-service/repositories"

	"github.com/google/uuid"
)

type SubmissionService interface {
	SubmitVerification(ctx context.Context, doctorPublicID uuid.UUID) (*dto.SubmitVerificationResponse, error)
}

type DefaultSubmissionService struct {
	doctorRepo  repositories.DoctorRepository
	licenseRepo repositories.LicenseRepository
	qualRepo    repositories.QualificationRepository
	clinicRepo  repositories.ClinicRepository
	docRepo     repositories.DocumentRepository
	historyRepo repositories.VerificationHistoryRepository
	jobRepo     repositories.JobRepository
}

func NewSubmissionService(
	doctorRepo repositories.DoctorRepository,
	licenseRepo repositories.LicenseRepository,
	qualRepo repositories.QualificationRepository,
	clinicRepo repositories.ClinicRepository,
	docRepo repositories.DocumentRepository,
	historyRepo repositories.VerificationHistoryRepository,
	jobRepo repositories.JobRepository,
) SubmissionService {
	return &DefaultSubmissionService{
		doctorRepo:  doctorRepo,
		licenseRepo: licenseRepo,
		qualRepo:    qualRepo,
		clinicRepo:  clinicRepo,
		docRepo:     docRepo,
		historyRepo: historyRepo,
		jobRepo:     jobRepo,
	}
}

func (s *DefaultSubmissionService) SubmitVerification(ctx context.Context, doctorPublicID uuid.UUID) (*dto.SubmitVerificationResponse, error) {
	// 1. Resolve Doctor
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorPublicID)
	if err != nil || doc == nil {
		return nil, errors.New("doctor account not found")
	}

	var missingChecklist []string

	// Checklist 1: Mobile Verified
	if !doc.MobileVerified {
		missingChecklist = append(missingChecklist, "Mobile number verification pending")
	}

	// Checklist 2: Medical License
	licenses, err := s.licenseRepo.FindByDoctorID(ctx, doc.ID)
	if err != nil || len(licenses) == 0 {
		missingChecklist = append(missingChecklist, "At least one medical registration license is required")
	}

	// Checklist 3: Qualifications
	quals, err := s.qualRepo.FindByDoctorID(ctx, doc.ID)
	if err != nil || len(quals) == 0 {
		missingChecklist = append(missingChecklist, "At least one medical qualification degree is required")
	}

	// Checklist 4: Clinics
	clinics, err := s.clinicRepo.FindByDoctorID(ctx, doc.ID)
	if err != nil || len(clinics) == 0 {
		missingChecklist = append(missingChecklist, "At least one clinic listing is required")
	}

	// Checklist 5: Mandatory Documents
	uploadedDocs, err := s.docRepo.FindByDoctorID(ctx, doc.ID)
	if err != nil {
		uploadedDocs = []entities.DoctorDocument{}
	}

	hasRegistrationCert := false
	hasDegreeCert := false
	hasGovtID := false

	for _, d := range uploadedDocs {
		switch d.DocumentType {
		case entities.DocumentTypeRegistrationCertificate:
			hasRegistrationCert = true
		case entities.DocumentTypeMBBSCertificate, entities.DocumentTypeMDCertificate, entities.DocumentTypeMedicalDegreeCertificate:
			hasDegreeCert = true
		case entities.DocumentTypeAadhaar, entities.DocumentTypePAN, entities.DocumentTypePassport:
			hasGovtID = true
		}
	}

	if !hasRegistrationCert {
		missingChecklist = append(missingChecklist, "Medical Registration Certificate document is missing")
	}
	if !hasDegreeCert {
		missingChecklist = append(missingChecklist, "Medical Degree Certificate document is missing")
	}
	if !hasGovtID {
		missingChecklist = append(missingChecklist, "Government Identity proof (Aadhaar, PAN, or Passport) is missing")
	}

	if len(missingChecklist) > 0 {
		return nil, fmt.Errorf("verification submission rejected. Incomplete profile checklist:\n- %s", strings.Join(missingChecklist, "\n- "))
	}

	// 2. Transition Status to PENDING
	doc.Status = entities.DoctorStatusPending
	if err := s.doctorRepo.Update(ctx, doc); err != nil {
		return nil, fmt.Errorf("failed to update doctor status: %w", err)
	}

	// 3. Record Audit Log in Verification History
	remarks := "Doctor submitted profile and all mandatory documents for verification."
	history := &entities.VerificationHistory{
		DoctorID:    doc.ID,
		Action:      "SUBMISSION_COMPLETED",
		Status:      string(entities.DoctorStatusPending),
		Remarks:     &remarks,
		PerformedAt: time.Now(),
	}
	_ = s.historyRepo.Create(ctx, history)

	// 4. Enqueue Verification Background Job in QUEUED status
	if s.jobRepo != nil {
		job := &entities.VerificationJob{
			JobID:      uuid.New(),
			DoctorID:   doc.PublicID,
			JobType:    entities.JobTypeFullPipeline,
			Status:     entities.JobStatusQueued,
			Priority:   1,
			MaxRetries: 3,
		}
		_ = s.jobRepo.Create(ctx, job)
	}

	return &dto.SubmitVerificationResponse{
		Message:     "Doctor verification application submitted successfully. Your profile has been queued for background OCR and council verification.",
		PublicID:    doc.PublicID,
		Status:      string(doc.Status),
		SubmittedAt: time.Now(),
	}, nil
}
