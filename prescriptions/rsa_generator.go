package prescriptions

import (
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"errors"
	"fmt"
	"time"

	"doctor-service/entities"

	"github.com/google/uuid"
)

type RSADigitalPrescription struct {
	PrescriptionID   uuid.UUID `json:"prescription_id"`
	DoctorID         uuid.UUID `json:"doctor_id"`
	PatientID        string    `json:"patient_id"`
	Diagnosis        string    `json:"diagnosis"`
	Medicines        []string  `json:"medicines"`
	DigitalSignature string    `json:"digital_signature"` // Base64 encoded RSA-SHA256 signature
	PublicKeyPEM     string    `json:"public_key_pem"`     // Public Key for external verification
	QRPayload        string    `json:"qr_payload"`
	IssuedAt         time.Time `json:"issued_at"`
}

type RSAPrescriptionGenerator struct {
	privateKey *rsa.PrivateKey
	publicKey  *rsa.PublicKey
}

func NewRSAPrescriptionGenerator() (*RSAPrescriptionGenerator, error) {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return nil, fmt.Errorf("failed to generate RSA keypair: %w", err)
	}
	return &RSAPrescriptionGenerator{
		privateKey: key,
		publicKey:  &key.PublicKey,
	}, nil
}

func (g *RSAPrescriptionGenerator) IssuePrescription(doctor *entities.Doctor, patientID, diagnosis string, medicines []string) (*RSADigitalPrescription, error) {
	if doctor.Status != entities.DoctorStatusVerified || !doctor.PrescriptionEnabled {
		return nil, fmt.Errorf("doctor '%s' is not authorized to issue digital prescriptions", doctor.PublicID)
	}

	prescriptionID := uuid.New()
	issuedAt := time.Now()
	medsJSON, _ := json.Marshal(medicines)

	// 1. Signature Input
	signatureInput := fmt.Sprintf("%s|%s|%s|%s|%s|%s",
		prescriptionID.String(),
		doctor.PublicID.String(),
		patientID,
		diagnosis,
		string(medsJSON),
		issuedAt.Format(time.RFC3339),
	)

	// 2. Sign using RSA-SHA256 Private Key
	hashed := sha256.Sum256([]byte(signatureInput))
	signatureBytes, err := rsa.SignPKCS1v15(rand.Reader, g.privateKey, crypto.SHA256, hashed[:])
	if err != nil {
		return nil, fmt.Errorf("RSA signature generation failed: %w", err)
	}
	digitalSignature := base64.StdEncoding.EncodeToString(signatureBytes)

	// Export Public Key as PEM
	pubBytes, err := x509.MarshalPKIXPublicKey(g.publicKey)
	var pubPEM string
	if err == nil {
		pubBlock := &pem.Block{Type: "PUBLIC KEY", Bytes: pubBytes}
		pubPEM = string(pem.EncodeToMemory(pubBlock))
	}

	// 3. Generate QR Payload
	qrData := map[string]interface{}{
		"pid":  prescriptionID.String(),
		"doc":  doctor.PublicID.String(),
		"name": doctor.FirstName + " " + doctor.LastName,
		"pat":  patientID,
		"sig":  digitalSignature[:24],
		"ts":   issuedAt.Unix(),
		"url":  fmt.Sprintf("https://practo-doctor.portal/prescriptions/%s/verify", prescriptionID.String()),
	}

	qrJSON, _ := json.Marshal(qrData)
	qrPayload := base64.StdEncoding.EncodeToString(qrJSON)

	return &RSADigitalPrescription{
		PrescriptionID:   prescriptionID,
		DoctorID:         doctor.PublicID,
		PatientID:        patientID,
		Diagnosis:        diagnosis,
		Medicines:        medicines,
		DigitalSignature: digitalSignature,
		PublicKeyPEM:     pubPEM,
		QRPayload:        qrPayload,
		IssuedAt:         issuedAt,
	}, nil
}

func VerifyRSASignature(p *RSADigitalPrescription) (bool, error) {
	if p.PublicKeyPEM == "" || p.DigitalSignature == "" {
		return false, errors.New("missing public key or digital signature")
	}

	block, _ := pem.Decode([]byte(p.PublicKeyPEM))
	if block == nil {
		return false, errors.New("failed to decode public key PEM")
	}

	pub, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		return false, fmt.Errorf("failed to parse public key: %w", err)
	}
	rsaPub, ok := pub.(*rsa.PublicKey)
	if !ok {
		return false, errors.New("invalid RSA public key type")
	}

	medsJSON, _ := json.Marshal(p.Medicines)
	signatureInput := fmt.Sprintf("%s|%s|%s|%s|%s|%s",
		p.PrescriptionID.String(),
		p.DoctorID.String(),
		p.PatientID,
		p.Diagnosis,
		string(medsJSON),
		p.IssuedAt.Format(time.RFC3339),
	)

	hashed := sha256.Sum256([]byte(signatureInput))
	sigBytes, err := base64.StdEncoding.DecodeString(p.DigitalSignature)
	if err != nil {
		return false, fmt.Errorf("failed to decode signature base64: %w", err)
	}

	err = rsa.VerifyPKCS1v15(rsaPub, crypto.SHA256, hashed[:], sigBytes)
	if err != nil {
		return false, nil // Invalid signature
	}

	return true, nil
}
