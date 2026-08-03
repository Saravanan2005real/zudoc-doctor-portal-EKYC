package repositories

import (
	"context"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type AdminActionRepository interface {
	Create(ctx context.Context, action *entities.AdminAction) error
	FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.AdminAction, error)
}

type GormAdminActionRepository struct {
	db *gorm.DB
}

func NewAdminActionRepository(db *gorm.DB) AdminActionRepository {
	return &GormAdminActionRepository{db: db}
}

func (r *GormAdminActionRepository) Create(ctx context.Context, action *entities.AdminAction) error {
	return r.db.WithContext(ctx).Create(action).Error
}

func (r *GormAdminActionRepository) FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.AdminAction, error) {
	var actions []entities.AdminAction
	err := r.db.WithContext(ctx).Where("doctor_id = ?", doctorID).Order("created_at DESC").Find(&actions).Error
	return actions, err
}
