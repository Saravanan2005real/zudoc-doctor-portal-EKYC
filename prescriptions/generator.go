package prescriptions

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"time"

	"doctor-service/entities"

	"github.com/google/uuid"
)

type DigitalPrescription struct {
	PrescriptionID   uuid.UUID `json:"prescription_id"`
	DoctorID         uuid.UUID `json:"doctor_id"`
	PatientID        string    `json:"patient_id"`
	Diagnosis        string    `json:"diagnosis"`
	Medicines        []string  `json:"medicines"`
	DigitalSignature string    `json:"digital_signature"`
	QRPayload        string    `json:"qr_payload"`
	IssuedAt         time.Time `json:"issued_at"`
}

type PrescriptionGenerator struct {
	signingSecret []byte
}

func NewPrescriptionGenerator(secretKey string) *PrescriptionGenerator {
	if secretKey == "" {
		secretKey = "digital-prescription-signing-rsa-secret-key"
	}
	return &PrescriptionGenerator{
		signingSecret: []byte(secretKey),
	}
}

func (g *PrescriptionGenerator) IssuePrescription(doctor *entities.Doctor, patientID, diagnosis string, medicines []string) (*DigitalPrescription, error) {
	if doctor.Status != entities.DoctorStatusVerified || !doctor.PrescriptionEnabled {
		return nil, fmt.Errorf("doctor '%s' is not authorized to issue digital prescriptions", doctor.PublicID)
	}

	prescriptionID := uuid.New()
	issuedAt := time.Now()

	medsJSON, _ := json.Marshal(medicines)

	// 1. Generate Tamper-Proof Digital Signature
	signatureInput := fmt.Sprintf("%s|%s|%s|%s|%s|%s",
		prescriptionID.String(),
		doctor.PublicID.String(),
		patientID,
		diagnosis,
		string(medsJSON),
		issuedAt.Format(time.RFC3339),
	)

	h := hmac.New(sha256.New, g.signingSecret)
	h.Write([]byte(signatureInput))
	digitalSignature := hex.EncodeToString(h.Sum(nil))

	// 2. Generate Base64 QR Code Payload
	qrData := map[string]interface{}{
		"pid":  prescriptionID.String(),
		"doc":  doctor.PublicID.String(),
		"name": doctor.FirstName + " " + doctor.LastName,
		"pat":  patientID,
		"sig":  digitalSignature[:16], // Signature fingerprint
		"ts":   issuedAt.Unix(),
		"url":  fmt.Sprintf("https://practo-doctor.portal/prescriptions/%s/verify", prescriptionID.String()),
	}

	qrJSON, _ := json.Marshal(qrData)
	qrPayload := base64.StdEncoding.EncodeToString(qrJSON)

	return &DigitalPrescription{
		PrescriptionID:   prescriptionID,
		DoctorID:         doctor.PublicID,
		PatientID:        patientID,
		Diagnosis:        diagnosis,
		Medicines:        medicines,
		DigitalSignature: digitalSignature,
		QRPayload:        qrPayload,
		IssuedAt:         issuedAt,
	}, nil
}

func (g *PrescriptionGenerator) VerifySignature(p *DigitalPrescription) bool {
	medsJSON, _ := json.Marshal(p.Medicines)
	signatureInput := fmt.Sprintf("%s|%s|%s|%s|%s|%s",
		p.PrescriptionID.String(),
		p.DoctorID.String(),
		p.PatientID,
		p.Diagnosis,
		string(medsJSON),
		p.IssuedAt.Format(time.RFC3339),
	)

	h := hmac.New(sha256.New, g.signingSecret)
	h.Write([]byte(signatureInput))
	expectedSig := hex.EncodeToString(h.Sum(nil))

	return hmac.Equal([]byte(p.DigitalSignature), []byte(expectedSig))
}
