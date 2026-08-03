package security

import (
	"context"
	"net/http"

	"doctor-service/entities"
	"doctor-service/repositories"

	"github.com/google/uuid"
)

type PrescriptionAuthGuard struct {
	doctorRepo repositories.DoctorRepository
}

func NewPrescriptionAuthGuard(doctorRepo repositories.DoctorRepository) *PrescriptionAuthGuard {
	return &PrescriptionAuthGuard{doctorRepo: doctorRepo}
}

func (g *PrescriptionAuthGuard) RequireVerifiedDoctorForPrescription(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		docIDStr := r.Header.Get("X-Doctor-Public-ID")
		if docIDStr == "" {
			http.Error(w, `{"error":"Unauthorized: Missing X-Doctor-Public-ID header"}`, http.StatusUnauthorized)
			return
		}

		docUUID, err := uuid.Parse(docIDStr)
		if err != nil {
			http.Error(w, `{"error":"Unauthorized: Invalid X-Doctor-Public-ID header format"}`, http.StatusUnauthorized)
			return
		}

		doc, err := g.doctorRepo.FindByPublicID(r.Context(), docUUID)
		if err != nil || doc == nil {
			http.Error(w, `{"error":"Unauthorized: Doctor account not found"}`, http.StatusUnauthorized)
			return
		}

		if doc.Status != entities.DoctorStatusVerified {
			http.Error(w, `{"error":"Forbidden: Doctor verification incomplete. Only VERIFIED doctors can generate digital prescriptions or conduct teleconsultations."}`, http.StatusForbidden)
			return
		}

		if !doc.PrescriptionEnabled {
			http.Error(w, `{"error":"Forbidden: Digital prescription enablement is disabled on this profile. Please contact medical compliance."}`, http.StatusForbidden)
			return
		}

		// Inject verified doctor into context
		ctx := context.WithValue(r.Context(), "verified_doctor", doc)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}
