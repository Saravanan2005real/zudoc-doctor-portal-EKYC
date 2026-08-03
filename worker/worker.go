package worker

import (
	"context"
	"log"
	"time"

	"doctor-service/entities"
	"doctor-service/repositories"
	"doctor-service/services"
)

type VerificationWorker struct {
	jobRepo         repositories.JobRepository
	pipelineService services.VerificationPipelineService
	pollInterval    time.Duration
	stopChan        chan struct{}
}

func NewVerificationWorker(jobRepo repositories.JobRepository, pipelineService services.VerificationPipelineService, pollInterval time.Duration) *VerificationWorker {
	if pollInterval <= 0 {
		pollInterval = 2 * time.Second
	}
	return &VerificationWorker{
		jobRepo:         jobRepo,
		pipelineService: pipelineService,
		pollInterval:    pollInterval,
		stopChan:        make(chan struct{}),
	}
}

func (w *VerificationWorker) Start(ctx context.Context) {
	log.Println("[BACKGROUND WORKER] Verification Worker started listening for QUEUED jobs...")
	ticker := time.NewTicker(w.pollInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			log.Println("[BACKGROUND WORKER] Worker shutting down...")
			return
		case <-w.stopChan:
			log.Println("[BACKGROUND WORKER] Worker stopped.")
			return
		case <-ticker.C:
			w.processNextJob(ctx)
		}
	}
}

func (w *VerificationWorker) Stop() {
	close(w.stopChan)
}

func (w *VerificationWorker) processNextJob(ctx context.Context) {
	job, err := w.jobRepo.FetchNextQueuedJob(ctx)
	if err != nil || job == nil {
		return // No queued jobs
	}

	log.Printf("[BACKGROUND WORKER] Picked Job '%s' (Type: %s, DoctorID: %s) for processing...", job.JobID, job.JobType, job.DoctorID)

	if job.JobType == entities.JobTypeFullPipeline || job.JobType == entities.JobTypeOCR {
		if err := w.pipelineService.ProcessVerificationJob(ctx, job.JobID); err != nil {
			log.Printf("[BACKGROUND WORKER] Job '%s' failed: %v", job.JobID, err)
		} else {
			log.Printf("[BACKGROUND WORKER] Job '%s' processed successfully!", job.JobID)
		}
	}
}
