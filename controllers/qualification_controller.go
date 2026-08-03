package controllers

import (
	"encoding/json"
	"net/http"

	"doctor-service/dto"
	"doctor-service/services"

	"github.com/google/uuid"
)

type QualificationController struct {
	qualService services.QualificationService
}

func NewQualificationController(qualService services.QualificationService) *QualificationController {
	return &QualificationController{qualService: qualService}
}

func (c *QualificationController) HandleQualifications(w http.ResponseWriter, r *http.Request) {
	docIDStr := r.Header.Get("X-Doctor-Public-ID")
	docUUID, err := uuid.Parse(docIDStr)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Missing or invalid X-Doctor-Public-ID header"})
		return
	}

	switch r.Method {
	case http.MethodPost:
		var req dto.AddQualificationRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid request payload"})
			return
		}
		resp, err := c.qualService.AddQualification(r.Context(), docUUID, req)
		if err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		c.respondJSON(w, http.StatusCreated, resp)

	case http.MethodGet:
		resp, err := c.qualService.GetQualifications(r.Context(), docUUID)
		if err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		c.respondJSON(w, http.StatusOK, resp)

	case http.MethodDelete:
		qualIDStr := r.URL.Query().Get("id")
		qualUUID, err := uuid.Parse(qualIDStr)
		if err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Missing or invalid qualification id parameter"})
			return
		}
		if err := c.qualService.DeleteQualification(r.Context(), qualUUID, docUUID); err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		c.respondJSON(w, http.StatusOK, map[string]string{"message": "Qualification deleted successfully"})

	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func (c *QualificationController) respondJSON(w http.ResponseWriter, status int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
