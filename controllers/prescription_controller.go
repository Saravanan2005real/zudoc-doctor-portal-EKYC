package controllers

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/google/uuid"
)

type CreatePrescriptionRequest struct {
	PatientID string   `json:"patient_id" binding:"required"`
	Diagnosis string   `json:"diagnosis" binding:"required"`
	Medicines []string `json:"medicines" binding:"required"`
}

type PrescriptionController struct{}

func NewPrescriptionController() *PrescriptionController {
	return &PrescriptionController{}
}

func (c *PrescriptionController) CreatePrescription(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req CreatePrescriptionRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		_ = json.NewEncoder(w).Encode(map[string]string{"error": "Invalid prescription payload"})
		return
	}

	prescriptionID := uuid.New()
	response := map[string]interface{}{
		"prescription_id": prescriptionID,
		"status":          "ISSUED",
		"patient_id":      req.PatientID,
		"diagnosis":       req.Diagnosis,
		"medicines":       req.Medicines,
		"digital_signature": map[string]string{
			"signed_by": r.Header.Get("X-Doctor-Public-ID"),
			"timestamp": time.Now().Format(time.RFC3339),
			"algorithm": "RSA-SHA256-PKCS1v15",
		},
		"message": "Digital prescription created successfully.",
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	_ = json.NewEncoder(w).Encode(response)
}
