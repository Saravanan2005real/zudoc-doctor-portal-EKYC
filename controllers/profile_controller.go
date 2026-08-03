package controllers

import (
	"encoding/json"
	"net/http"

	"doctor-service/dto"
	"doctor-service/services"

	"github.com/google/uuid"
)

type ProfileController struct {
	profileService services.ProfileService
}

func NewProfileController(profileService services.ProfileService) *ProfileController {
	return &ProfileController{profileService: profileService}
}

func (c *ProfileController) HandleProfile(w http.ResponseWriter, r *http.Request) {
	// Extract doctor public_id from request header or query parameter
	docIDStr := r.Header.Get("X-Doctor-Public-ID")
	if docIDStr == "" {
		docIDStr = r.URL.Query().Get("doctor_id")
	}

	docUUID, err := uuid.Parse(docIDStr)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Missing or invalid X-Doctor-Public-ID header"})
		return
	}

	switch r.Method {
	case http.MethodPut:
		var req dto.UpdateProfileRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid JSON payload"})
			return
		}
		resp, err := c.profileService.UpdateProfile(r.Context(), docUUID, req)
		if err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		c.respondJSON(w, http.StatusOK, resp)

	case http.MethodGet:
		resp, err := c.profileService.GetProfile(r.Context(), docUUID)
		if err != nil {
			c.respondJSON(w, http.StatusNotFound, map[string]string{"error": err.Error()})
			return
		}
		c.respondJSON(w, http.StatusOK, resp)

	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func (c *ProfileController) respondJSON(w http.ResponseWriter, status int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
