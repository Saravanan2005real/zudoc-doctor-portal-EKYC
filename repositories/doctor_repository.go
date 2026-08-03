package repositories

import (
	"context"
	"errors"
	"time"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type DoctorRepository interface {
	Create(ctx context.Context, doctor *entities.Doctor) error
	FindByEmail(ctx context.Context, email string) (*entities.Doctor, error)
	FindByMobile(ctx context.Context, mobile string) (*entities.Doctor, error)
	FindByIdentifier(ctx context.Context, identifier string) (*entities.Doctor, error)
	FindByPublicID(ctx context.Context, publicID uuid.UUID) (*entities.Doctor, error)
	Update(ctx context.Context, doctor *entities.Doctor) error
	IncrementFailedLogin(ctx context.Context, doctorID uuid.UUID, maxAttempts int, lockDuration time.Duration) (int, bool, error)
	ResetFailedLogin(ctx context.Context, doctorID uuid.UUID) error
	MarkMobileVerified(ctx context.Context, doctorID uuid.UUID) error
}

type GormDoctorRepository struct {
	db *gorm.DB
}

func NewDoctorRepository(db *gorm.DB) DoctorRepository {
	return &GormDoctorRepository{db: db}
}

func (r *GormDoctorRepository) Create(ctx context.Context, doctor *entities.Doctor) error {
	return r.db.WithContext(ctx).Create(doctor).Error
}

func (r *GormDoctorRepository) FindByEmail(ctx context.Context, email string) (*entities.Doctor, error) {
	var doc entities.Doctor
	err := r.db.WithContext(ctx).Where("email = ?", email).First(&doc).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	return &doc, err
}

func (r *GormDoctorRepository) FindByMobile(ctx context.Context, mobile string) (*entities.Doctor, error) {
	var doc entities.Doctor
	err := r.db.WithContext(ctx).Where("mobile = ?", mobile).First(&doc).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	return &doc, err
}

func (r *GormDoctorRepository) FindByIdentifier(ctx context.Context, identifier string) (*entities.Doctor, error) {
	var doc entities.Doctor
	err := r.db.WithContext(ctx).Where("email = ? OR mobile = ?", identifier, identifier).First(&doc).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	return &doc, err
}

func (r *GormDoctorRepository) FindByPublicID(ctx context.Context, publicID uuid.UUID) (*entities.Doctor, error) {
	var doc entities.Doctor
	err := r.db.WithContext(ctx).Where("public_id = ?", publicID).First(&doc).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	return &doc, err
}

func (r *GormDoctorRepository) Update(ctx context.Context, doctor *entities.Doctor) error {
	return r.db.WithContext(ctx).Save(doctor).Error
}

func (r *GormDoctorRepository) IncrementFailedLogin(ctx context.Context, doctorID uuid.UUID, maxAttempts int, lockDuration time.Duration) (int, bool, error) {
	var doc entities.Doctor
	if err := r.db.WithContext(ctx).First(&doc, "id = ?", doctorID).Error; err != nil {
		return 0, false, err
	}

	doc.FailedLoginAttempts++
	isLocked := false
	if doc.FailedLoginAttempts >= maxAttempts {
		lockedUntil := time.Now().Add(lockDuration)
		doc.AccountLockedUntil = &lockedUntil
		isLocked = true
	}

	err := r.db.WithContext(ctx).Model(&doc).Updates(map[string]interface{}{
		"failed_login_attempts": doc.FailedLoginAttempts,
		"account_locked_until":  doc.AccountLockedUntil,
	}).Error

	return doc.FailedLoginAttempts, isLocked, err
}

func (r *GormDoctorRepository) ResetFailedLogin(ctx context.Context, doctorID uuid.UUID) error {
	now := time.Now()
	return r.db.WithContext(ctx).Model(&entities.Doctor{}).Where("id = ?", doctorID).Updates(map[string]interface{}{
		"failed_login_attempts": 0,
		"account_locked_until":  nil,
		"last_login_at":         &now,
	}).Error
}

func (r *GormDoctorRepository) MarkMobileVerified(ctx context.Context, doctorID uuid.UUID) error {
	return r.db.WithContext(ctx).Model(&entities.Doctor{}).Where("id = ?", doctorID).Update("mobile_verified", true).Error
}
