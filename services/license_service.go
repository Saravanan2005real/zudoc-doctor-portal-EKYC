package services

import (
	"context"
	"errors"
	"time"

	"doctor-service/dto"
	"doctor-service/entities"
	"doctor-service/repositories"

	"github.com/google/uuid"
)

type LicenseService interface {
	AddLicense(ctx context.Context, doctorID uuid.UUID, req dto.AddLicenseRequest) (*dto.LicenseResponse, error)
	GetLicenses(ctx context.Context, doctorID uuid.UUID) ([]dto.LicenseResponse, error)
	DeleteLicense(ctx context.Context, licenseID, doctorID uuid.UUID) error
}

type DefaultLicenseService struct {
	doctorRepo  repositories.DoctorRepository
	licenseRepo repositories.LicenseRepository
}

func NewLicenseService(doctorRepo repositories.DoctorRepository, licenseRepo repositories.LicenseRepository) LicenseService {
	return &DefaultLicenseService{doctorRepo: doctorRepo, licenseRepo: licenseRepo}
}

func (s *DefaultLicenseService) AddLicense(ctx context.Context, doctorID uuid.UUID, req dto.AddLicenseRequest) (*dto.LicenseResponse, error) {
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorID)
	if err != nil || doc == nil {
		return nil, errors.New("doctor not found")
	}

	var issueDate, expiryDate *time.Time
	if req.IssueDate != "" {
		if t, err := time.Parse("2006-01-02", req.IssueDate); err == nil {
			issueDate = &t
		}
	}
	if req.ExpiryDate != "" {
		if t, err := time.Parse("2006-01-02", req.ExpiryDate); err == nil {
			expiryDate = &t
		}
	}

	license := &entities.DoctorLicense{
		DoctorID:            doc.ID,
		RegistrationNumber:  req.RegistrationNumber,
		RegistrationCouncil: req.RegistrationCouncil,
		RegistrationYear:    req.RegistrationYear,
		IssueDate:           issueDate,
		ExpiryDate:          expiryDate,
		LicenseStatus:       "ACTIVE",
		VerificationStatus:  entities.VerificationStatusUnverified,
	}

	if err := s.licenseRepo.Create(ctx, license); err != nil {
		return nil, err
	}

	return &dto.LicenseResponse{
		LicenseID:           license.LicenseID,
		RegistrationNumber:  license.RegistrationNumber,
		RegistrationCouncil: license.RegistrationCouncil,
		RegistrationYear:    license.RegistrationYear,
		LicenseStatus:       license.LicenseStatus,
		VerificationStatus:  string(license.VerificationStatus),
		CreatedAt:           license.CreatedAt,
	}, nil
}

func (s *DefaultLicenseService) GetLicenses(ctx context.Context, doctorID uuid.UUID) ([]dto.LicenseResponse, error) {
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorID)
	if err != nil || doc == nil {
		return nil, errors.New("doctor not found")
	}

	licenses, err := s.licenseRepo.FindByDoctorID(ctx, doc.ID)
	if err != nil {
		return nil, err
	}

	var res []dto.LicenseResponse
	for _, l := range licenses {
		res = append(res, dto.LicenseResponse{
			LicenseID:           l.LicenseID,
			RegistrationNumber:  l.RegistrationNumber,
			RegistrationCouncil: l.RegistrationCouncil,
			RegistrationYear:    l.RegistrationYear,
			LicenseStatus:       l.LicenseStatus,
			VerificationStatus:  string(l.VerificationStatus),
			CreatedAt:           l.CreatedAt,
		})
	}
	return res, nil
}

func (s *DefaultLicenseService) DeleteLicense(ctx context.Context, licenseID, doctorID uuid.UUID) error {
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorID)
	if err != nil || doc == nil {
		return errors.New("doctor not found")
	}
	return s.licenseRepo.Delete(ctx, licenseID, doc.ID)
}
