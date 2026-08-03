package repositories

import (
	"context"
	"errors"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type RefreshTokenRepository interface {
	Create(ctx context.Context, token *entities.RefreshToken) error
	FindByHash(ctx context.Context, tokenHash string) (*entities.RefreshToken, error)
	Revoke(ctx context.Context, tokenHash string) error
	RevokeAllForDoctor(ctx context.Context, doctorID uuid.UUID) error
}

type GormRefreshTokenRepository struct {
	db *gorm.DB
}

func NewRefreshTokenRepository(db *gorm.DB) RefreshTokenRepository {
	return &GormRefreshTokenRepository{db: db}
}

func (r *GormRefreshTokenRepository) Create(ctx context.Context, token *entities.RefreshToken) error {
	return r.db.WithContext(ctx).Create(token).Error
}

func (r *GormRefreshTokenRepository) FindByHash(ctx context.Context, tokenHash string) (*entities.RefreshToken, error) {
	var token entities.RefreshToken
	err := r.db.WithContext(ctx).Where("token_hash = ?", tokenHash).First(&token).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	return &token, err
}

func (r *GormRefreshTokenRepository) Revoke(ctx context.Context, tokenHash string) error {
	return r.db.WithContext(ctx).Model(&entities.RefreshToken{}).Where("token_hash = ?", tokenHash).Update("is_revoked", true).Error
}

func (r *GormRefreshTokenRepository) RevokeAllForDoctor(ctx context.Context, doctorID uuid.UUID) error {
	return r.db.WithContext(ctx).Model(&entities.RefreshToken{}).Where("doctor_id = ?", doctorID).Update("is_revoked", true).Error
}
