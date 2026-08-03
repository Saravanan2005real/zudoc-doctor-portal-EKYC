package controllers

import (
	"encoding/json"
	"net/http"

	"doctor-service/dto"
	"doctor-service/services"

	"github.com/google/uuid"
)

type ClinicController struct {
	clinicService services.ClinicService
}

func NewClinicController(clinicService services.ClinicService) *ClinicController {
	return &ClinicController{clinicService: clinicService}
}

func (c *ClinicController) HandleClinics(w http.ResponseWriter, r *http.Request) {
	docIDStr := r.Header.Get("X-Doctor-Public-ID")
	docUUID, err := uuid.Parse(docIDStr)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Missing or invalid X-Doctor-Public-ID header"})
		return
	}

	switch r.Method {
	case http.MethodPost:
		var req dto.AddClinicRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid request payload"})
			return
		}
		resp, err := c.clinicService.AddClinic(r.Context(), docUUID, req)
		if err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		c.respondJSON(w, http.StatusCreated, resp)

	case http.MethodGet:
		resp, err := c.clinicService.GetClinics(r.Context(), docUUID)
		if err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		c.respondJSON(w, http.StatusOK, resp)

	case http.MethodDelete:
		clinicIDStr := r.URL.Query().Get("id")
		clinicUUID, err := uuid.Parse(clinicIDStr)
		if err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Missing or invalid clinic id parameter"})
			return
		}
		if err := c.clinicService.DeleteClinic(r.Context(), clinicUUID, docUUID); err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		c.respondJSON(w, http.StatusOK, map[string]string{"message": "Clinic deleted successfully"})

	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func (c *ClinicController) respondJSON(w http.ResponseWriter, status int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
