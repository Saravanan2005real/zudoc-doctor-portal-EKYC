package security_test

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"doctor-service/entities"
	"doctor-service/repositories"
	"doctor-service/security"

	"github.com/google/uuid"
)

type mockDoctorRepo struct {
	repositories.DoctorRepository
	doc *entities.Doctor
}

func (m *mockDoctorRepo) FindByPublicID(ctx context.Context, publicID uuid.UUID) (*entities.Doctor, error) {
	if m.doc != nil && m.doc.PublicID == publicID {
		return m.doc, nil
	}
	return nil, nil
}

func TestPrescriptionGuardBlocksUnverifiedDoctors(t *testing.T) {
	pubID := uuid.New()
	unverifiedDoc := &entities.Doctor{
		ID:                  uuid.New(),
		PublicID:            pubID,
		Status:              entities.DoctorStatusPending, // Not VERIFIED
		PrescriptionEnabled: false,
	}

	guard := security.NewPrescriptionAuthGuard(&mockDoctorRepo{doc: unverifiedDoc})

	dummyHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("prescription created"))
	})

	guardedHandler := guard.RequireVerifiedDoctorForPrescription(dummyHandler)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/prescriptions", nil)
	req.Header.Set("X-Doctor-Public-ID", pubID.String())
	rec := httptest.NewRecorder()

	guardedHandler.ServeHTTP(rec, req)

	if rec.Code != http.StatusForbidden {
		t.Fatalf("expected HTTP 403 Forbidden for pending doctor, got HTTP %d", rec.Code)
	}
}

func TestPrescriptionGuardAllowsVerifiedDoctors(t *testing.T) {
	pubID := uuid.New()
	verifiedDoc := &entities.Doctor{
		ID:                  uuid.New(),
		PublicID:            pubID,
		Status:              entities.DoctorStatusVerified,
		PrescriptionEnabled: true,
	}

	guard := security.NewPrescriptionAuthGuard(&mockDoctorRepo{doc: verifiedDoc})

	dummyHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("prescription created"))
	})

	guardedHandler := guard.RequireVerifiedDoctorForPrescription(dummyHandler)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/prescriptions", nil)
	req.Header.Set("X-Doctor-Public-ID", pubID.String())
	rec := httptest.NewRecorder()

	guardedHandler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected HTTP 200 OK for verified doctor, got HTTP %d", rec.Code)
	}
}
