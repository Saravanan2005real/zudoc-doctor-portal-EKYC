package controllers

import (
	"encoding/json"
	"net/http"

	"doctor-service/dto"
	"doctor-service/services"

	"github.com/google/uuid"
)

type AdminController struct {
	adminService services.AdminReviewService
}

func NewAdminController(adminService services.AdminReviewService) *AdminController {
	return &AdminController{adminService: adminService}
}

func (c *AdminController) GetDoctorVerificationDetail(w http.ResponseWriter, r *http.Request) {
	docIDStr := r.URL.Query().Get("id")
	if docIDStr == "" {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Missing doctor id parameter"})
		return
	}

	docUUID, err := uuid.Parse(docIDStr)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid doctor id format"})
		return
	}

	resp, err := c.adminService.GetDoctorVerificationDetail(r.Context(), docUUID)
	if err != nil {
		c.respondJSON(w, http.StatusNotFound, map[string]string{"error": err.Error()})
		return
	}

	c.respondJSON(w, http.StatusOK, resp)
}

func (c *AdminController) AssignDoctor(w http.ResponseWriter, r *http.Request) {
	docIDStr := r.URL.Query().Get("id")
	docUUID, err := uuid.Parse(docIDStr)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid doctor id"})
		return
	}

	adminIDStr := r.Header.Get("X-Admin-ID")
	adminUUID, err := uuid.Parse(adminIDStr)
	if err != nil {
		adminUUID = uuid.New() // Fallback demo ID
	}

	if err := c.adminService.AssignReviewer(r.Context(), docUUID, adminUUID); err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	c.respondJSON(w, http.StatusOK, map[string]string{"message": "Doctor verification case assigned successfully"})
}

func (c *AdminController) ApproveDoctor(w http.ResponseWriter, r *http.Request) {
	docIDStr := r.URL.Query().Get("id")
	docUUID, err := uuid.Parse(docIDStr)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid doctor id"})
		return
	}

	adminIDStr := r.Header.Get("X-Admin-ID")
	adminUUID, err := uuid.Parse(adminIDStr)
	if err != nil {
		adminUUID = uuid.New()
	}

	var req dto.ApproveDoctorRequest
	_ = json.NewDecoder(r.Body).Decode(&req)

	if err := c.adminService.ApproveDoctor(r.Context(), docUUID, adminUUID, req, r.RemoteAddr, r.UserAgent()); err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	c.respondJSON(w, http.StatusOK, map[string]string{"message": "Doctor verification approved successfully. Digital prescription features enabled."})
}

func (c *AdminController) RejectDoctor(w http.ResponseWriter, r *http.Request) {
	docIDStr := r.URL.Query().Get("id")
	docUUID, err := uuid.Parse(docIDStr)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid doctor id"})
		return
	}

	adminIDStr := r.Header.Get("X-Admin-ID")
	adminUUID, err := uuid.Parse(adminIDStr)
	if err != nil {
		adminUUID = uuid.New()
	}

	var req dto.RejectDoctorRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Reason == "" {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Rejection reason is required"})
		return
	}

	if err := c.adminService.RejectDoctor(r.Context(), docUUID, adminUUID, req, r.RemoteAddr, r.UserAgent()); err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	c.respondJSON(w, http.StatusOK, map[string]string{"message": "Doctor verification application rejected."})
}

func (c *AdminController) RequestDocuments(w http.ResponseWriter, r *http.Request) {
	docIDStr := r.URL.Query().Get("id")
	docUUID, err := uuid.Parse(docIDStr)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid doctor id"})
		return
	}

	adminIDStr := r.Header.Get("X-Admin-ID")
	adminUUID, err := uuid.Parse(adminIDStr)
	if err != nil {
		adminUUID = uuid.New()
	}

	var req dto.RequestDocumentsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid request payload"})
		return
	}

	if err := c.adminService.RequestDocuments(r.Context(), docUUID, adminUUID, req, r.RemoteAddr, r.UserAgent()); err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	c.respondJSON(w, http.StatusOK, map[string]string{"message": "Additional document request dispatched to doctor."})
}

func (c *AdminController) AddNote(w http.ResponseWriter, r *http.Request) {
	docIDStr := r.URL.Query().Get("id")
	docUUID, err := uuid.Parse(docIDStr)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid doctor id"})
		return
	}

	adminIDStr := r.Header.Get("X-Admin-ID")
	adminUUID, err := uuid.Parse(adminIDStr)
	if err != nil {
		adminUUID = uuid.New()
	}

	var req dto.AddNoteRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Note == "" {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Note text is required"})
		return
	}

	note, err := c.adminService.AddNote(r.Context(), docUUID, adminUUID, req)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	c.respondJSON(w, http.StatusCreated, note)
}

func (c *AdminController) respondJSON(w http.ResponseWriter, status int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
