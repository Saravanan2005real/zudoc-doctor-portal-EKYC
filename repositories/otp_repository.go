package repositories

import (
	"context"
	"errors"
	"time"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type OTPRepository interface {
	Create(ctx context.Context, otp *entities.OTPVerification) error
	FindLatestActive(ctx context.Context, doctorID uuid.UUID, purpose entities.OTPPurpose) (*entities.OTPVerification, error)
	IncrementAttempt(ctx context.Context, otpID uuid.UUID) error
	MarkVerified(ctx context.Context, otpID uuid.UUID) error
	InvalidatePreviousOTPs(ctx context.Context, doctorID uuid.UUID, purpose entities.OTPPurpose) error
}

type GormOTPRepository struct {
	db *gorm.DB
}

func NewOTPRepository(db *gorm.DB) OTPRepository {
	return &GormOTPRepository{db: db}
}

func (r *GormOTPRepository) Create(ctx context.Context, otp *entities.OTPVerification) error {
	return r.db.WithContext(ctx).Create(otp).Error
}

func (r *GormOTPRepository) FindLatestActive(ctx context.Context, doctorID uuid.UUID, purpose entities.OTPPurpose) (*entities.OTPVerification, error) {
	var otp entities.OTPVerification
	err := r.db.WithContext(ctx).
		Where("doctor_id = ? AND purpose = ? AND verified_at IS NULL", doctorID, purpose).
		Order("created_at DESC").
		First(&otp).Error

	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	return &otp, err
}

func (r *GormOTPRepository) IncrementAttempt(ctx context.Context, otpID uuid.UUID) error {
	return r.db.WithContext(ctx).
		Model(&entities.OTPVerification{}).
		Where("id = ?", otpID).
		UpdateColumn("attempt_count", gorm.Expr("attempt_count + 1")).Error
}

func (r *GormOTPRepository) MarkVerified(ctx context.Context, otpID uuid.UUID) error {
	now := time.Now()
	return r.db.WithContext(ctx).
		Model(&entities.OTPVerification{}).
		Where("id = ?", otpID).
		Update("verified_at", &now).Error
}

func (r *GormOTPRepository) InvalidatePreviousOTPs(ctx context.Context, doctorID uuid.UUID, purpose entities.OTPPurpose) error {
	now := time.Now()
	return r.db.WithContext(ctx).
		Model(&entities.OTPVerification{}).
		Where("doctor_id = ? AND purpose = ? AND verified_at IS NULL", doctorID, purpose).
		Update("expires_at", now).Error
}
