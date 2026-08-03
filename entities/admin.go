package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type AdminRole string

const (
	AdminRoleReviewer       AdminRole = "REVIEWER"
	AdminRoleSeniorReviewer AdminRole = "SENIOR_REVIEWER"
	AdminRoleSuperAdmin     AdminRole = "SUPER_ADMIN"
)

type AdminUser struct {
	ID           uuid.UUID      `gorm:"primaryKey" json:"id"`
	FullName     string         `gorm:"size:100;not null" json:"full_name"`
	Email        string         `gorm:"size:255;uniqueIndex;not null" json:"email"`
	PasswordHash string         `gorm:"size:255;not null" json:"-"`
	Role         AdminRole      `gorm:"size:50;default:'REVIEWER';not null" json:"role"`
	IsActive     bool           `gorm:"default:true;not null" json:"is_active"`
	CreatedAt    time.Time      `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt    time.Time      `gorm:"autoUpdateTime" json:"updated_at"`
	DeletedAt    gorm.DeletedAt `gorm:"index" json:"-"`
}

func (a *AdminUser) BeforeCreate(tx *gorm.DB) (err error) {
	if a.ID == uuid.Nil {
		a.ID = uuid.New()
	}
	return nil
}
