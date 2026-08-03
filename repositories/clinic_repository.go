package repositories

import (
	"context"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type ClinicRepository interface {
	Create(ctx context.Context, clinic *entities.DoctorClinic) error
	FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.DoctorClinic, error)
	Delete(ctx context.Context, clinicID, doctorID uuid.UUID) error
}

type GormClinicRepository struct {
	db *gorm.DB
}

func NewClinicRepository(db *gorm.DB) ClinicRepository {
	return &GormClinicRepository{db: db}
}

func (r *GormClinicRepository) Create(ctx context.Context, clinic *entities.DoctorClinic) error {
	return r.db.WithContext(ctx).Create(clinic).Error
}

func (r *GormClinicRepository) FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.DoctorClinic, error) {
	var clinics []entities.DoctorClinic
	err := r.db.WithContext(ctx).Where("doctor_id = ?", doctorID).Find(&clinics).Error
	return clinics, err
}

func (r *GormClinicRepository) Delete(ctx context.Context, clinicID, doctorID uuid.UUID) error {
	return r.db.WithContext(ctx).Where("clinic_id = ? AND doctor_id = ?", clinicID, doctorID).Delete(&entities.DoctorClinic{}).Error
}
