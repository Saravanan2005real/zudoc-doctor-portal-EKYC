package prescriptions_test

import (
	"testing"

	"doctor-service/entities"
	"doctor-service/prescriptions"

	"github.com/google/uuid"
)

func TestDigitalPrescriptionGenerationAndVerification(t *testing.T) {
	gen := prescriptions.NewPrescriptionGenerator("test-signing-secret")

	doctor := &entities.Doctor{
		ID:                  uuid.New(),
		PublicID:            uuid.New(),
		FirstName:           "Rahul",
		LastName:            "Kumar",
		Status:              entities.DoctorStatusVerified,
		PrescriptionEnabled: true,
	}

	p, err := gen.IssuePrescription(doctor, "PATIENT-1001", "Acute Bronchitis", []string{"Amoxicillin 500mg", "Paracetamol 650mg"})
	if err != nil {
		t.Fatalf("failed to issue prescription: %v", err)
	}

	if p.DigitalSignature == "" || p.QRPayload == "" {
		t.Fatalf("expected non-empty digital signature and QR payload")
	}

	if !gen.VerifySignature(p) {
		t.Fatalf("digital signature verification failed")
	}

	// Tamper test
	p.Diagnosis = "Tampered Diagnosis"
	if gen.VerifySignature(p) {
		t.Fatalf("expected digital signature verification to fail for tampered prescription")
	}
}
