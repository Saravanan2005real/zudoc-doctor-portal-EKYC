package entities

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type DocumentType string
type OCRStatus string

const (
	DocumentTypeRegistrationCertificate DocumentType = "REGISTRATION_CERTIFICATE"
	DocumentTypeMBBSCertificate         DocumentType = "MBBS_CERTIFICATE"
	DocumentTypeMDCertificate           DocumentType = "MD_CERTIFICATE"
	DocumentTypeAadhaar                 DocumentType = "AADHAAR"
	DocumentTypePAN                     DocumentType = "PAN"
	DocumentTypePassport                DocumentType = "PASSPORT"

	OCRStatusPending    OCRStatus = "PENDING"
	OCRStatusProcessing OCRStatus = "PROCESSING"
	OCRStatusCompleted  OCRStatus = "COMPLETED"
	OCRStatusFailed     OCRStatus = "FAILED"
)

type DoctorDocument struct {
	DocumentID       uuid.UUID      `gorm:"primaryKey" json:"document_id"`
	DoctorID         uuid.UUID      `gorm:"not null;index" json:"doctor_id"`
	DocumentType     DocumentType   `gorm:"size:50;not null;index" json:"document_type"`
	FileURL          string         `gorm:"type:text;not null" json:"file_url"`
	OriginalFilename string         `gorm:"size:255;not null" json:"original_filename"`
	MIMEType         string         `gorm:"size:100;not null" json:"mime_type"`
	FileSize         int64          `gorm:"not null" json:"file_size"`
	FileHash         string         `gorm:"size:64;not null;index" json:"file_hash"`
	ResolutionWidth  *int           `json:"resolution_width,omitempty"`
	ResolutionHeight *int           `json:"resolution_height,omitempty"`
	Version          int            `gorm:"default:1;not null" json:"version"`
	IsLatest         bool           `gorm:"default:true;not null" json:"is_latest"`
	OCRStatus        OCRStatus      `gorm:"size:50;default:'PENDING';not null" json:"ocr_status"`
	UploadedAt       time.Time      `gorm:"autoCreateTime" json:"uploaded_at"`
	UpdatedAt        time.Time      `gorm:"autoUpdateTime" json:"updated_at"`
	DeletedAt        gorm.DeletedAt `gorm:"index" json:"-"`

	// Relations
	OCRResults []DocumentOCRResult `gorm:"foreignKey:DocumentID;constraint:OnDelete:CASCADE" json:"ocr_results,omitempty"`
}

func (d *DoctorDocument) BeforeCreate(tx *gorm.DB) (err error) {
	if d.DocumentID == uuid.Nil {
		d.DocumentID = uuid.New()
	}
	return nil
}
