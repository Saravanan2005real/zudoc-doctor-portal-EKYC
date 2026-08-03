package controllers

import (
	"encoding/json"
	"net/http"

	"doctor-service/entities"
	"doctor-service/services"

	"github.com/google/uuid"
)

type DocumentController struct {
	docService services.DocumentService
}

func NewDocumentController(docService services.DocumentService) *DocumentController {
	return &DocumentController{docService: docService}
}

func (c *DocumentController) HandleDocuments(w http.ResponseWriter, r *http.Request) {
	docIDStr := r.Header.Get("X-Doctor-Public-ID")
	docUUID, err := uuid.Parse(docIDStr)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Missing or invalid X-Doctor-Public-ID header"})
		return
	}

	switch r.Method {
	case http.MethodPost:
		// Multipart Form parsing (max 12MB limit)
		if err := r.ParseMultipartForm(12 * 1024 * 1024); err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Failed to parse multipart form payload"})
			return
		}

		file, header, err := r.FormFile("file")
		if err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Missing file field in multipart request"})
			return
		}

		docTypeStr := r.FormValue("document_type")
		if docTypeStr == "" {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Missing document_type field"})
			return
		}

		resp, err := c.docService.UploadDocument(
			r.Context(),
			docUUID,
			entities.DocumentType(docTypeStr),
			file,
			header.Filename,
			header.Size,
		)
		if err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}

		c.respondJSON(w, http.StatusCreated, resp)

	case http.MethodGet:
		resp, err := c.docService.GetDoctorDocuments(r.Context(), docUUID)
		if err != nil {
			c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		c.respondJSON(w, http.StatusOK, resp)

	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func (c *DocumentController) respondJSON(w http.ResponseWriter, status int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
