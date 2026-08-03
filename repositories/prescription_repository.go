package repositories

import (
	"context"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type PrescriptionRepository interface {
	Create(ctx context.Context, p *entities.Prescription) error
	FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.Prescription, error)
	FindByID(ctx context.Context, id uuid.UUID) (*entities.Prescription, error)
}

type GormPrescriptionRepository struct {
	db *gorm.DB
}

func NewPrescriptionRepository(db *gorm.DB) PrescriptionRepository {
	return &GormPrescriptionRepository{db: db}
}

func (r *GormPrescriptionRepository) Create(ctx context.Context, p *entities.Prescription) error {
	return r.db.WithContext(ctx).Create(p).Error
}

func (r *GormPrescriptionRepository) FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.Prescription, error) {
	var list []entities.Prescription
	err := r.db.WithContext(ctx).Where("doctor_id = ?", doctorID).Order("issued_at DESC").Find(&list).Error
	return list, err
}

func (r *GormPrescriptionRepository) FindByID(ctx context.Context, id uuid.UUID) (*entities.Prescription, error) {
	var p entities.Prescription
	err := r.db.WithContext(ctx).Where("prescription_id = ?", id).First(&p).Error
	return &p, err
}
