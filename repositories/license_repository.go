package repositories

import (
	"context"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type LicenseRepository interface {
	Create(ctx context.Context, license *entities.DoctorLicense) error
	FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.DoctorLicense, error)
	Delete(ctx context.Context, licenseID, doctorID uuid.UUID) error
}

type GormLicenseRepository struct {
	db *gorm.DB
}

func NewLicenseRepository(db *gorm.DB) LicenseRepository {
	return &GormLicenseRepository{db: db}
}

func (r *GormLicenseRepository) Create(ctx context.Context, license *entities.DoctorLicense) error {
	return r.db.WithContext(ctx).Create(license).Error
}

func (r *GormLicenseRepository) FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.DoctorLicense, error) {
	var licenses []entities.DoctorLicense
	err := r.db.WithContext(ctx).Where("doctor_id = ?", doctorID).Find(&licenses).Error
	return licenses, err
}

func (r *GormLicenseRepository) Delete(ctx context.Context, licenseID, doctorID uuid.UUID) error {
	return r.db.WithContext(ctx).Where("license_id = ? AND doctor_id = ?", licenseID, doctorID).Delete(&entities.DoctorLicense{}).Error
}
