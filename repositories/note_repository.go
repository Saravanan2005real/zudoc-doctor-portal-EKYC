package repositories

import (
	"context"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type NoteRepository interface {
	Create(ctx context.Context, note *entities.DoctorNote) error
	FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.DoctorNote, error)
}

type GormNoteRepository struct {
	db *gorm.DB
}

func NewNoteRepository(db *gorm.DB) NoteRepository {
	return &GormNoteRepository{db: db}
}

func (r *GormNoteRepository) Create(ctx context.Context, note *entities.DoctorNote) error {
	return r.db.WithContext(ctx).Create(note).Error
}

func (r *GormNoteRepository) FindByDoctorID(ctx context.Context, doctorID uuid.UUID) ([]entities.DoctorNote, error) {
	var notes []entities.DoctorNote
	err := r.db.WithContext(ctx).Where("doctor_id = ?", doctorID).Order("created_at DESC").Find(&notes).Error
	return notes, err
}
