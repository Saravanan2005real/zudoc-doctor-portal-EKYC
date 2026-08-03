package controllers

import (
	"encoding/json"
	"net/http"

	"doctor-service/services"

	"github.com/google/uuid"
)

type SubmissionController struct {
	submissionService services.SubmissionService
}

func NewSubmissionController(submissionService services.SubmissionService) *SubmissionController {
	return &SubmissionController{submissionService: submissionService}
}

func (c *SubmissionController) SubmitVerification(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	docIDStr := r.Header.Get("X-Doctor-Public-ID")
	docUUID, err := uuid.Parse(docIDStr)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Missing or invalid X-Doctor-Public-ID header"})
		return
	}

	resp, err := c.submissionService.SubmitVerification(r.Context(), docUUID)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	c.respondJSON(w, http.StatusOK, resp)
}

func (c *SubmissionController) respondJSON(w http.ResponseWriter, status int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
