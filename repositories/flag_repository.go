package repositories

import (
	"context"
	"time"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type FlagRepository interface {
	Create(ctx context.Context, flag *entities.VerificationFlag) error
	FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.VerificationFlag, error)
	ResolveFlag(ctx context.Context, flagID, adminID uuid.UUID) error
}

type GormFlagRepository struct {
	db *gorm.DB
}

func NewFlagRepository(db *gorm.DB) FlagRepository {
	return &GormFlagRepository{db: db}
}

func (r *GormFlagRepository) Create(ctx context.Context, flag *entities.VerificationFlag) error {
	return r.db.WithContext(ctx).Create(flag).Error
}

func (r *GormFlagRepository) FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.VerificationFlag, error) {
	var flags []entities.VerificationFlag
	err := r.db.WithContext(ctx).Where("doctor_id = ?", doctorID).Order("created_at DESC").Find(&flags).Error
	return flags, err
}

func (r *GormFlagRepository) ResolveFlag(ctx context.Context, flagID, adminID uuid.UUID) error {
	now := time.Now()
	return r.db.WithContext(ctx).Model(&entities.VerificationFlag{}).
		Where("id = ?", flagID).
		Updates(map[string]interface{}{
			"resolved":    true,
			"resolved_by": &adminID,
			"resolved_at": &now,
		}).Error
}
