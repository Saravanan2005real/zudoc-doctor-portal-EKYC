package controllers

import (
	"encoding/json"
	"net/http"

	"doctor-service/dto"
	"doctor-service/services"

	"github.com/google/uuid"
)

type LicenseController struct {
	licenseService services.LicenseService
}

func NewLicenseController(licenseService services.LicenseService) *LicenseController {
	return &LicenseController{licenseService: licenseService}
}

func (c *LicenseController) HandleLicenses(w http.ResponseWriter, r *http.Request) {
	docIDStr := r.Header.Get("X-Doctor-Public-ID")
	docUUID, err := uuid.Parse(docIDStr)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Missing or invalid X-Doctor-Public-ID header"})
		return
	}

	switch r.Method {
	case http.MethodPost:
		var req dto.AddLicenseRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid request payload"})
			return
		}
		resp, err := c.licenseService.AddLicense(r.Context(), docUUID, req)
		if err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		c.respondJSON(w, http.StatusCreated, resp)

	case http.MethodGet:
		resp, err := c.licenseService.GetLicenses(r.Context(), docUUID)
		if err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		c.respondJSON(w, http.StatusOK, resp)

	case http.MethodDelete:
		licenseIDStr := r.URL.Query().Get("id")
		licenseUUID, err := uuid.Parse(licenseIDStr)
		if err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Missing or invalid license id parameter"})
			return
		}
		if err := c.licenseService.DeleteLicense(r.Context(), licenseUUID, docUUID); err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		c.respondJSON(w, http.StatusOK, map[string]string{"message": "License deleted successfully"})

	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func (c *LicenseController) respondJSON(w http.ResponseWriter, status int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
