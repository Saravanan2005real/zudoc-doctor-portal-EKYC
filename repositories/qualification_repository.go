package repositories

import (
	"context"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type QualificationRepository interface {
	Create(ctx context.Context, qual *entities.DoctorQualification) error
	FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.DoctorQualification, error)
	Delete(ctx context.Context, qualificationID, doctorID uuid.UUID) error
}

type GormQualificationRepository struct {
	db *gorm.DB
}

func NewQualificationRepository(db *gorm.DB) QualificationRepository {
	return &GormQualificationRepository{db: db}
}

func (r *GormQualificationRepository) Create(ctx context.Context, qual *entities.DoctorQualification) error {
	return r.db.WithContext(ctx).Create(qual).Error
}

func (r *GormQualificationRepository) FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.DoctorQualification, error) {
	var quals []entities.DoctorQualification
	err := r.db.WithContext(ctx).Where("doctor_id = ?", doctorID).Find(&quals).Error
	return quals, err
}

func (r *GormQualificationRepository) Delete(ctx context.Context, qualificationID, doctorID uuid.UUID) error {
	return r.db.WithContext(ctx).Where("qualification_id = ? AND doctor_id = ?", qualificationID, doctorID).Delete(&entities.DoctorQualification{}).Error
}
