package repositories

import (
	"context"
	"errors"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type OCRRepository interface {
	Create(ctx context.Context, ocrResult *entities.DocumentOCRResult) error
	FindByDocumentID(ctx context.Context, documentID uuid.UUID) ([]entities.DocumentOCRResult, error)
	FindLatestByDocumentID(ctx context.Context, documentID uuid.UUID) (*entities.DocumentOCRResult, error)
}

type GormOCRRepository struct {
	db *gorm.DB
}

func NewOCRRepository(db *gorm.DB) OCRRepository {
	return &GormOCRRepository{db: db}
}

func (r *GormOCRRepository) Create(ctx context.Context, ocrResult *entities.DocumentOCRResult) error {
	return r.db.WithContext(ctx).Create(ocrResult).Error
}

func (r *GormOCRRepository) FindByDocumentID(ctx context.Context, documentID uuid.UUID) ([]entities.DocumentOCRResult, error) {
	var results []entities.DocumentOCRResult
	err := r.db.WithContext(ctx).Where("document_id = ?", documentID).Order("processed_at DESC").Find(&results).Error
	return results, err
}

func (r *GormOCRRepository) FindLatestByDocumentID(ctx context.Context, documentID uuid.UUID) (*entities.DocumentOCRResult, error) {
	var result entities.DocumentOCRResult
	err := r.db.WithContext(ctx).Where("document_id = ?", documentID).Order("processed_at DESC").First(&result).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	return &result, err
}
