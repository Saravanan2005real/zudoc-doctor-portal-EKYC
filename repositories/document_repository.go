package repositories

import (
	"context"
	"errors"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type DocumentRepository interface {
	Create(ctx context.Context, doc *entities.DoctorDocument) error
	FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.DoctorDocument, error)
	FindByDoctorAndType(ctx context.Context, doctorID uuid.UUID, docType entities.DocumentType) ([]entities.DoctorDocument, error)
	FindLatestByDoctorAndType(ctx context.Context, doctorID uuid.UUID, docType entities.DocumentType) (*entities.DoctorDocument, error)
	FindByHash(ctx context.Context, doctorID uuid.UUID, fileHash string) (*entities.DoctorDocument, error)
	MarkPreviousVersionsNotLatest(ctx context.Context, doctorID uuid.UUID, docType entities.DocumentType) error
}

type GormDocumentRepository struct {
	db *gorm.DB
}

func NewDocumentRepository(db *gorm.DB) DocumentRepository {
	return &GormDocumentRepository{db: db}
}

func (r *GormDocumentRepository) Create(ctx context.Context, doc *entities.DoctorDocument) error {
	return r.db.WithContext(ctx).Create(doc).Error
}

func (r *GormDocumentRepository) FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.DoctorDocument, error) {
	var docs []entities.DoctorDocument
	err := r.db.WithContext(ctx).Where("doctor_id = ? AND is_latest = true", doctorID).Find(&docs).Error
	return docs, err
}

func (r *GormDocumentRepository) FindByDoctorAndType(ctx context.Context, doctorID uuid.UUID, docType entities.DocumentType) ([]entities.DoctorDocument, error) {
	var docs []entities.DoctorDocument
	err := r.db.WithContext(ctx).Where("doctor_id = ? AND document_type = ?", doctorID, docType).Order("version DESC").Find(&docs).Error
	return docs, err
}

func (r *GormDocumentRepository) FindLatestByDoctorAndType(ctx context.Context, doctorID uuid.UUID, docType entities.DocumentType) (*entities.DoctorDocument, error) {
	var doc entities.DoctorDocument
	err := r.db.WithContext(ctx).Where("doctor_id = ? AND document_type = ? AND is_latest = true", doctorID, docType).First(&doc).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	return &doc, err
}

func (r *GormDocumentRepository) FindByHash(ctx context.Context, doctorID uuid.UUID, fileHash string) (*entities.DoctorDocument, error) {
	var doc entities.DoctorDocument
	err := r.db.WithContext(ctx).Where("doctor_id = ? AND file_hash = ?", doctorID, fileHash).First(&doc).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	return &doc, err
}

func (r *GormDocumentRepository) MarkPreviousVersionsNotLatest(ctx context.Context, doctorID uuid.UUID, docType entities.DocumentType) error {
	return r.db.WithContext(ctx).
		Model(&entities.DoctorDocument{}).
		Where("doctor_id = ? AND document_type = ? AND is_latest = true", doctorID, docType).
		Update("is_latest", false).Error
}
