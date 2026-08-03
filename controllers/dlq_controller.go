package controllers

import (
	"encoding/json"
	"net/http"

	"doctor-service/entities"
	"doctor-service/repositories"

	"github.com/google/uuid"
)

type DLQController struct {
	dlqRepo repositories.DLQRepository
	jobRepo repositories.JobRepository
}

func NewDLQController(dlqRepo repositories.DLQRepository, jobRepo repositories.JobRepository) *DLQController {
	return &DLQController{dlqRepo: dlqRepo, jobRepo: jobRepo}
}

func (c *DLQController) ListDeadJobs(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	deadJobs, err := c.dlqRepo.FindAll(r.Context())
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		_ = json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(deadJobs)
}

func (c *DLQController) RetryDeadJob(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	idStr := r.URL.Query().Get("id")
	deadUUID, err := uuid.Parse(idStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		_ = json.NewEncoder(w).Encode(map[string]string{"error": "Invalid dead job id"})
		return
	}

	deadJob, err := c.dlqRepo.FindByID(r.Context(), deadUUID)
	if err != nil || deadJob == nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		_ = json.NewEncoder(w).Encode(map[string]string{"error": "Dead job record not found"})
		return
	}

	// Requeue Job into verification_jobs
	newJob := &entities.VerificationJob{
		JobID:      uuid.New(),
		DoctorID:   deadJob.DoctorID,
		JobType:    entities.JobTypeFullPipeline,
		Status:     entities.JobStatusQueued,
		Priority:   2, // High priority for manual retry
		MaxRetries: 3,
	}

	if err := c.jobRepo.Create(r.Context(), newJob); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		_ = json.NewEncoder(w).Encode(map[string]string{"error": "Failed to requeue job"})
		return
	}

	// Remove from DLQ
	_ = c.dlqRepo.Delete(r.Context(), deadUUID)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"message":     "Failed job re-queued successfully for verification",
		"new_job_id":  newJob.JobID,
		"requeued_at": newJob.CreatedAt,
	})
}
