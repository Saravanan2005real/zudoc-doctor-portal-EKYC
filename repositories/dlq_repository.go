package repositories

import (
	"context"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type DLQRepository interface {
	Create(ctx context.Context, deadJob *entities.VerificationDeadJob) error
	FindAll(ctx context.Context) ([]entities.VerificationDeadJob, error)
	FindByID(ctx context.Context, id uuid.UUID) (*entities.VerificationDeadJob, error)
	Delete(ctx context.Context, id uuid.UUID) error
}

type GormDLQRepository struct {
	db *gorm.DB
}

func NewDLQRepository(db *gorm.DB) DLQRepository {
	return &GormDLQRepository{db: db}
}

func (r *GormDLQRepository) Create(ctx context.Context, deadJob *entities.VerificationDeadJob) error {
	return r.db.WithContext(ctx).Create(deadJob).Error
}

func (r *GormDLQRepository) FindAll(ctx context.Context) ([]entities.VerificationDeadJob, error) {
	var jobs []entities.VerificationDeadJob
	err := r.db.WithContext(ctx).Order("failed_at DESC").Find(&jobs).Error
	return jobs, err
}

func (r *GormDLQRepository) FindByID(ctx context.Context, id uuid.UUID) (*entities.VerificationDeadJob, error) {
	var job entities.VerificationDeadJob
	err := r.db.WithContext(ctx).Where("id = ?", id).First(&job).Error
	return &job, err
}

func (r *GormDLQRepository) Delete(ctx context.Context, id uuid.UUID) error {
	return r.db.WithContext(ctx).Where("id = ?", id).Delete(&entities.VerificationDeadJob{}).Error
}
