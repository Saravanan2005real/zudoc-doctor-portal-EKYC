package services_test

import (
	"context"
	"testing"

	"doctor-service/dto"
	"doctor-service/entities"
	"doctor-service/notifications"
	"doctor-service/repositories"
	"doctor-service/services"
	"doctor-service/verification/comparison"

	"github.com/google/uuid"
)

type mockAdminActionRepo struct {
	repositories.AdminActionRepository
	actions []entities.AdminAction
}

func (m *mockAdminActionRepo) Create(ctx context.Context, action *entities.AdminAction) error {
	m.actions = append(m.actions, *action)
	return nil
}

type mockFlagRepo struct {
	repositories.FlagRepository
	flags []entities.VerificationFlag
}

func (m *mockFlagRepo) Create(ctx context.Context, flag *entities.VerificationFlag) error {
	m.flags = append(m.flags, *flag)
	return nil
}

type mockNoteRepo struct {
	repositories.NoteRepository
	notes []entities.DoctorNote
}

func (m *mockNoteRepo) Create(ctx context.Context, note *entities.DoctorNote) error {
	m.notes = append(m.notes, *note)
	return nil
}

func TestAdminApprovalEnablesPrescriptions(t *testing.T) {
	docID := uuid.New()
	pubID := uuid.New()
	adminID := uuid.New()

	doc := &entities.Doctor{
		ID:                  docID,
		PublicID:            pubID,
		Status:              entities.DoctorStatusPending,
		PrescriptionEnabled: false,
	}

	docRepo := &mockDoctorRepo{doc: doc}
	adminActionRepo := &mockAdminActionRepo{}

	adminSvc := services.NewAdminReviewService(
		docRepo,
		&mockLicenseRepo{},
		&mockQualRepo{},
		&mockClinicRepo{},
		&mockDocRepo{},
		nil,
		&mockHistoryRepo{},
		adminActionRepo,
		&mockNoteRepo{},
		&mockFlagRepo{},
		notifications.NewMockNotificationProvider(),
		comparison.NewComparator(),
	)

	err := adminSvc.ApproveDoctor(context.Background(), pubID, adminID, dto.ApproveDoctorRequest{Reason: "All credentials verified"}, "127.0.0.1", "TestUserAgent")
	if err != nil {
		t.Fatalf("expected approval to succeed, got error: %v", err)
	}

	if docRepo.doc.Status != entities.DoctorStatusVerified {
		t.Fatalf("expected doctor status to update to VERIFIED, got %s", docRepo.doc.Status)
	}

	if !docRepo.doc.PrescriptionEnabled {
		t.Fatalf("expected prescription_enabled to be true after admin approval")
	}

	if len(adminActionRepo.actions) != 1 || adminActionRepo.actions[0].Action != "APPROVE" {
		t.Fatalf("expected admin action APPROVE to be recorded in audit log")
	}
}

func TestAdminRequestDocuments(t *testing.T) {
	docID := uuid.New()
	pubID := uuid.New()
	adminID := uuid.New()

	doc := &entities.Doctor{
		ID:       docID,
		PublicID: pubID,
		Status:   entities.DoctorStatusManualReview,
	}

	docRepo := &mockDoctorRepo{doc: doc}
	flagRepo := &mockFlagRepo{}

	adminSvc := services.NewAdminReviewService(
		docRepo,
		&mockLicenseRepo{},
		&mockQualRepo{},
		&mockClinicRepo{},
		&mockDocRepo{},
		nil,
		&mockHistoryRepo{},
		&mockAdminActionRepo{},
		&mockNoteRepo{},
		flagRepo,
		notifications.NewMockNotificationProvider(),
		comparison.NewComparator(),
	)

	err := adminSvc.RequestDocuments(
		context.Background(),
		pubID,
		adminID,
		dto.RequestDocumentsRequest{
			RequiredDocuments: []string{"Registration Certificate"},
			Message:           "Original upload was blurry",
		},
		"127.0.0.1",
		"TestUserAgent",
	)

	if err != nil {
		t.Fatalf("expected request documents to succeed, got: %v", err)
	}

	if docRepo.doc.Status != entities.DoctorStatusDocumentsRequested {
		t.Fatalf("expected status to update to DOCUMENTS_REQUESTED, got %s", docRepo.doc.Status)
	}

	if len(flagRepo.flags) != 1 {
		t.Fatalf("expected verification flag to be created")
	}
}
