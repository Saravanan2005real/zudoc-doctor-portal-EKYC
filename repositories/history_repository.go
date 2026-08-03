package repositories

import (
	"context"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type VerificationHistoryRepository interface {
	Create(ctx context.Context, history *entities.VerificationHistory) error
	FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.VerificationHistory, error)
}

type GormVerificationHistoryRepository struct {
	db *gorm.DB
}

func NewVerificationHistoryRepository(db *gorm.DB) VerificationHistoryRepository {
	return &GormVerificationHistoryRepository{db: db}
}

func (r *GormVerificationHistoryRepository) Create(ctx context.Context, history *entities.VerificationHistory) error {
	return r.db.WithContext(ctx).Create(history).Error
}

func (r *GormVerificationHistoryRepository) FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.VerificationHistory, error) {
	var histories []entities.VerificationHistory
	err := r.db.WithContext(ctx).Where("doctor_id = ?", doctorID).Order("performed_at DESC").Find(&histories).Error
	return histories, err
}
