package prescriptions_test

import (
	"testing"

	"doctor-service/entities"
	"doctor-service/prescriptions"

	"github.com/google/uuid"
)

func TestRSADigitalPrescriptionSignatureAndPublicVerification(t *testing.T) {
	gen, err := prescriptions.NewRSAPrescriptionGenerator()
	if err != nil {
		t.Fatalf("failed to initialize RSA generator: %v", err)
	}

	doctor := &entities.Doctor{
		ID:                  uuid.New(),
		PublicID:            uuid.New(),
		FirstName:           "Rahul",
		LastName:            "Kumar",
		Status:              entities.DoctorStatusVerified,
		PrescriptionEnabled: true,
	}

	p, err := gen.IssuePrescription(doctor, "PATIENT-2002", "Acute Gastritis", []string{"Pantoprazole 40mg", "Domperidone 10mg"})
	if err != nil {
		t.Fatalf("failed to issue RSA signed prescription: %v", err)
	}

	if p.DigitalSignature == "" || p.PublicKeyPEM == "" || p.QRPayload == "" {
		t.Fatalf("expected non-empty RSA signature, public key PEM, and QR payload")
	}

	// Public verification using only Public Key PEM
	valid, err := prescriptions.VerifyRSASignature(p)
	if err != nil || !valid {
		t.Fatalf("expected RSA digital signature public verification to succeed, got valid=%v, err=%v", valid, err)
	}

	// Tamper test
	p.Diagnosis = "Tampered Diagnosis Text"
	validTampered, err := prescriptions.VerifyRSASignature(p)
	if validTampered {
		t.Fatalf("expected RSA signature verification to FAIL for tampered prescription")
	}
}
