package services_test

import (
	"context"
	"testing"

	"doctor-service/entities"
	"doctor-service/repositories"
	"doctor-service/services"

	"github.com/google/uuid"
)

type mockDoctorRepo struct {
	repositories.DoctorRepository
	doc *entities.Doctor
}

func (m *mockDoctorRepo) FindByPublicID(ctx context.Context, publicID uuid.UUID) (*entities.Doctor, error) {
	return m.doc, nil
}

func (m *mockDoctorRepo) Update(ctx context.Context, doctor *entities.Doctor) error {
	m.doc = doctor
	return nil
}

type mockLicenseRepo struct {
	repositories.LicenseRepository
	licenses []entities.DoctorLicense
}

func (m *mockLicenseRepo) FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.DoctorLicense, error) {
	return m.licenses, nil
}

type mockQualRepo struct {
	repositories.QualificationRepository
	quals []entities.DoctorQualification
}

func (m *mockQualRepo) FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.DoctorQualification, error) {
	return m.quals, nil
}

type mockClinicRepo struct {
	repositories.ClinicRepository
	clinics []entities.DoctorClinic
}

func (m *mockClinicRepo) FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.DoctorClinic, error) {
	return m.clinics, nil
}

type mockDocRepo struct {
	repositories.DocumentRepository
	docs []entities.DoctorDocument
}

func (m *mockDocRepo) FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.DoctorDocument, error) {
	return m.docs, nil
}

type mockHistoryRepo struct {
	repositories.VerificationHistoryRepository
}

func (m *mockHistoryRepo) Create(ctx context.Context, history *entities.VerificationHistory) error {
	return nil
}

type mockJobRepo struct {
	repositories.JobRepository
	createdJob *entities.VerificationJob
}

func (m *mockJobRepo) Create(ctx context.Context, job *entities.VerificationJob) error {
	m.createdJob = job
	return nil
}

func TestSubmissionChecklistRejectionWhenIncomplete(t *testing.T) {
	docID := uuid.New()
	pubID := uuid.New()

	doc := &entities.Doctor{
		ID:             docID,
		PublicID:       pubID,
		MobileVerified: false, // Incomplete!
		Status:         entities.DoctorStatusNotSubmitted,
	}

	submissionSvc := services.NewSubmissionService(
		&mockDoctorRepo{doc: doc},
		&mockLicenseRepo{licenses: nil},
		&mockQualRepo{quals: nil},
		&mockClinicRepo{clinics: nil},
		&mockDocRepo{docs: nil},
		&mockHistoryRepo{},
		&mockJobRepo{},
	)

	_, err := submissionSvc.SubmitVerification(context.Background(), pubID)
	if err == nil {
		t.Fatalf("expected incomplete submission to be rejected, but it passed")
	}
}

func TestSubmissionChecklistSuccessWhenComplete(t *testing.T) {
	docID := uuid.New()
	pubID := uuid.New()

	doc := &entities.Doctor{
		ID:             docID,
		PublicID:       pubID,
		MobileVerified: true,
		Status:         entities.DoctorStatusNotSubmitted,
	}

	licenses := []entities.DoctorLicense{{LicenseID: uuid.New(), DoctorID: docID}}
	quals := []entities.DoctorQualification{{QualificationID: uuid.New(), DoctorID: docID}}
	clinics := []entities.DoctorClinic{{ClinicID: uuid.New(), DoctorID: docID}}
	docs := []entities.DoctorDocument{
		{DocumentID: uuid.New(), DoctorID: docID, DocumentType: entities.DocumentTypeRegistrationCertificate},
		{DocumentID: uuid.New(), DoctorID: docID, DocumentType: entities.DocumentTypeMBBSCertificate},
		{DocumentID: uuid.New(), DoctorID: docID, DocumentType: entities.DocumentTypeAadhaar},
	}

	docRepoMock := &mockDoctorRepo{doc: doc}
	jobRepoMock := &mockJobRepo{}

	submissionSvc := services.NewSubmissionService(
		docRepoMock,
		&mockLicenseRepo{licenses: licenses},
		&mockQualRepo{quals: quals},
		&mockClinicRepo{clinics: clinics},
		&mockDocRepo{docs: docs},
		&mockHistoryRepo{},
		jobRepoMock,
	)

	resp, err := submissionSvc.SubmitVerification(context.Background(), pubID)
	if err != nil {
		t.Fatalf("expected submission to succeed, got error: %v", err)
	}

	if resp.Status != string(entities.DoctorStatusPending) {
		t.Fatalf("expected status PENDING, got %s", resp.Status)
	}

	if docRepoMock.doc.Status != entities.DoctorStatusPending {
		t.Fatalf("expected doctor status to update to PENDING")
	}

	if jobRepoMock.createdJob == nil || jobRepoMock.createdJob.Status != entities.JobStatusQueued {
		t.Fatalf("expected verification job to be enqueued in QUEUED status")
	}
}
