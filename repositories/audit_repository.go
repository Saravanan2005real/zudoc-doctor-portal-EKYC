package repositories

import (
	"context"

	"doctor-service/entities"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type AuditRepository interface {
	Create(ctx context.Context, event *entities.AuditEvent) error
	FindByActorID(ctx context.Context, actorID uuid.UUID) ([]entities.AuditEvent, error)
}

type GormAuditRepository struct {
	db *gorm.DB
}

func NewAuditRepository(db *gorm.DB) AuditRepository {
	return &GormAuditRepository{db: db}
}

func (r *GormAuditRepository) Create(ctx context.Context, event *entities.AuditEvent) error {
	return r.db.WithContext(ctx).Create(event).Error
}

func (r *GormAuditRepository) FindByActorID(ctx context.Context, actorID uuid.UUID) ([]entities.AuditEvent, error) {
	var events []entities.AuditEvent
	err := r.db.WithContext(ctx).Where("actor_id = ?", actorID).Order("timestamp DESC").Find(&events).Error
	return events, err
}
