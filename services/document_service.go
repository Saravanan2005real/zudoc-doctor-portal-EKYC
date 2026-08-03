package services

import (
	"context"
	"errors"
	"fmt"

	"doctor-service/dto"
	"doctor-service/entities"
	"doctor-service/repositories"
	"doctor-service/storage"

	"github.com/google/uuid"
)

type DocumentService interface {
	UploadDocument(ctx context.Context, doctorPublicID uuid.UUID, docType entities.DocumentType, file storage.ReadSeekerCloser, filename string, size int64) (*dto.DocumentUploadResponse, error)
	GetDoctorDocuments(ctx context.Context, doctorPublicID uuid.UUID) ([]dto.DocumentUploadResponse, error)
}

type DefaultDocumentService struct {
	doctorRepo      repositories.DoctorRepository
	docRepo         repositories.DocumentRepository
	storageProvider storage.StorageProvider
	validator       *storage.FileValidator
	scanner         storage.VirusScanner
}

func NewDocumentService(
	doctorRepo repositories.DoctorRepository,
	docRepo repositories.DocumentRepository,
	storageProvider storage.StorageProvider,
	validator *storage.FileValidator,
	scanner storage.VirusScanner,
) DocumentService {
	return &DefaultDocumentService{
		doctorRepo:      doctorRepo,
		docRepo:         docRepo,
		storageProvider: storageProvider,
		validator:       validator,
		scanner:         scanner,
	}
}

func (s *DefaultDocumentService) UploadDocument(ctx context.Context, doctorPublicID uuid.UUID, docType entities.DocumentType, file storage.ReadSeekerCloser, filename string, size int64) (*dto.DocumentUploadResponse, error) {
	defer file.Close()

	// 1. Resolve Doctor
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorPublicID)
	if err != nil || doc == nil {
		return nil, errors.New("doctor account not found")
	}

	// 2. Validate File (Extension, MIME, Size, Resolution, SHA-256 Hash)
	valRes, err := s.validator.Validate(file, filename, size)
	if err != nil {
		return nil, fmt.Errorf("file validation failed: %w", err)
	}

	// 3. Check Virus Scan Hook
	clean, scanMsg, err := s.scanner.Scan(ctx, file, filename)
	if err != nil || !clean {
		return nil, fmt.Errorf("virus scan check failed (%s): %w", scanMsg, err)
	}

	// 4. Check for exact duplicate file hash already uploaded by this doctor
	existingHashDoc, err := s.docRepo.FindByHash(ctx, doc.ID, valRes.FileHash)
	if err == nil && existingHashDoc != nil {
		return nil, fmt.Errorf("this exact file has already been uploaded as document type '%s'", existingHashDoc.DocumentType)
	}

	// 5. Versioning Check
	existingLatest, err := s.docRepo.FindLatestByDoctorAndType(ctx, doc.ID, docType)
	newVersion := 1
	if err == nil && existingLatest != nil {
		newVersion = existingLatest.Version + 1
	}

	// 6. Generate Isolated File Key & Upload to Storage Provider
	docID := uuid.New()
	storageKey := fmt.Sprintf("doctors/%s/documents/%s%s", doc.PublicID.String(), docID.String(), valRes.Extension)

	fileURL, err := s.storageProvider.Upload(ctx, file, storageKey, valRes.MIMEType)
	if err != nil {
		return nil, fmt.Errorf("storage upload failed: %w", err)
	}

	// 7. Mark previous versions as is_latest = false
	_ = s.docRepo.MarkPreviousVersionsNotLatest(ctx, doc.ID, docType)

	// 8. Create DoctorDocument Entity
	docEntity := &entities.DoctorDocument{
		DocumentID:       docID,
		DoctorID:         doc.ID,
		DocumentType:     docType,
		FileURL:          fileURL,
		OriginalFilename: valRes.OriginalFilename,
		MIMEType:         valRes.MIMEType,
		FileSize:         valRes.FileSize,
		FileHash:         valRes.FileHash,
		ResolutionWidth:  valRes.Width,
		ResolutionHeight: valRes.Height,
		Version:          newVersion,
		IsLatest:         true,
		OCRStatus:        entities.OCRStatusPending,
	}

	if err := s.docRepo.Create(ctx, docEntity); err != nil {
		return nil, fmt.Errorf("failed to save document metadata: %w", err)
	}

	return &dto.DocumentUploadResponse{
		DocumentID:       docEntity.DocumentID,
		DoctorID:         doc.PublicID,
		DocumentType:     string(docEntity.DocumentType),
		FileURL:          docEntity.FileURL,
		OriginalFilename: docEntity.OriginalFilename,
		MIMEType:         docEntity.MIMEType,
		FileSize:         docEntity.FileSize,
		FileHash:         docEntity.FileHash,
		Version:          docEntity.Version,
		IsLatest:         docEntity.IsLatest,
		OCRStatus:        string(docEntity.OCRStatus),
		UploadedAt:       docEntity.UploadedAt,
	}, nil
}

func (s *DefaultDocumentService) GetDoctorDocuments(ctx context.Context, doctorPublicID uuid.UUID) ([]dto.DocumentUploadResponse, error) {
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorPublicID)
	if err != nil || doc == nil {
		return nil, errors.New("doctor account not found")
	}

	documents, err := s.docRepo.FindByDoctorID(ctx, doc.ID)
	if err != nil {
		return nil, err
	}

	var res []dto.DocumentUploadResponse
	for _, d := range documents {
		res = append(res, dto.DocumentUploadResponse{
			DocumentID:       d.DocumentID,
			DoctorID:         doc.PublicID,
			DocumentType:     string(d.DocumentType),
			FileURL:          d.FileURL,
			OriginalFilename: d.OriginalFilename,
			MIMEType:         d.MIMEType,
			FileSize:         d.FileSize,
			FileHash:         d.FileHash,
			Version:          d.Version,
			IsLatest:         d.IsLatest,
			OCRStatus:        string(d.OCRStatus),
			UploadedAt:       d.UploadedAt,
		})
	}
	return res, nil
}
