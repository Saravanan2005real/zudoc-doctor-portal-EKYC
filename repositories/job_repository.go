package repositories

import (
	"context"
	"errors"
	"time"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type JobRepository interface {
	Create(ctx context.Context, job *entities.VerificationJob) error
	FetchNextQueuedJob(ctx context.Context) (*entities.VerificationJob, error)
	UpdateStatus(ctx context.Context, jobID uuid.UUID, status entities.JobStatus, lastError *string) error
	MarkRunning(ctx context.Context, jobID uuid.UUID) error
	MarkCompleted(ctx context.Context, jobID uuid.UUID) error
	MarkFailed(ctx context.Context, jobID uuid.UUID, errStr string) error
	FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.VerificationJob, error)
	FindByID(ctx context.Context, jobID uuid.UUID) (*entities.VerificationJob, error)
}

type GormJobRepository struct {
	db *gorm.DB
}

func NewJobRepository(db *gorm.DB) JobRepository {
	return &GormJobRepository{db: db}
}

func (r *GormJobRepository) Create(ctx context.Context, job *entities.VerificationJob) error {
	return r.db.WithContext(ctx).Create(job).Error
}

func (r *GormJobRepository) FetchNextQueuedJob(ctx context.Context) (*entities.VerificationJob, error) {
	var job entities.VerificationJob
	err := r.db.WithContext(ctx).
		Where("status = ?", entities.JobStatusQueued).
		Order("priority DESC, created_at ASC").
		First(&job).Error

	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	return &job, err
}

func (r *GormJobRepository) UpdateStatus(ctx context.Context, jobID uuid.UUID, status entities.JobStatus, lastError *string) error {
	updates := map[string]interface{}{
		"status": status,
	}
	if lastError != nil {
		updates["last_error"] = *lastError
	}
	return r.db.WithContext(ctx).Model(&entities.VerificationJob{}).Where("job_id = ?", jobID).Updates(updates).Error
}

func (r *GormJobRepository) MarkRunning(ctx context.Context, jobID uuid.UUID) error {
	now := time.Now()
	return r.db.WithContext(ctx).Model(&entities.VerificationJob{}).
		Where("job_id = ?", jobID).
		Updates(map[string]interface{}{
			"status":     entities.JobStatusRunning,
			"started_at": &now,
		}).Error
}

func (r *GormJobRepository) MarkCompleted(ctx context.Context, jobID uuid.UUID) error {
	now := time.Now()
	return r.db.WithContext(ctx).Model(&entities.VerificationJob{}).
		Where("job_id = ?", jobID).
		Updates(map[string]interface{}{
			"status":       entities.JobStatusSuccess,
			"completed_at": &now,
		}).Error
}

func (r *GormJobRepository) MarkFailed(ctx context.Context, jobID uuid.UUID, errStr string) error {
	now := time.Now()
	return r.db.WithContext(ctx).Model(&entities.VerificationJob{}).
		Where("job_id = ?", jobID).
		Updates(map[string]interface{}{
			"status":       entities.JobStatusFailed,
			"last_error":   errStr,
			"completed_at": &now,
		}).Error
}

func (r *GormJobRepository) FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.VerificationJob, error) {
	var jobs []entities.VerificationJob
	err := r.db.WithContext(ctx).Where("doctor_id = ?", doctorID).Order("created_at DESC").Find(&jobs).Error
	return jobs, err
}

func (r *GormJobRepository) FindByID(ctx context.Context, jobID uuid.UUID) (*entities.VerificationJob, error) {
	var job entities.VerificationJob
	err := r.db.WithContext(ctx).Where("job_id = ?", jobID).First(&job).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	return &job, err
}
