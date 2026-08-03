package services

import (
	"context"
	"errors"
	"time"

	"doctor-service/dto"
	"doctor-service/repositories"

	"github.com/google/uuid"
)

type ProfileService interface {
	UpdateProfile(ctx context.Context, doctorID uuid.UUID, req dto.UpdateProfileRequest) (*dto.DoctorProfileDTO, error)
	GetProfile(ctx context.Context, doctorID uuid.UUID) (*dto.DoctorProfileDTO, error)
}

type DefaultProfileService struct {
	doctorRepo repositories.DoctorRepository
}

func NewProfileService(doctorRepo repositories.DoctorRepository) ProfileService {
	return &DefaultProfileService{doctorRepo: doctorRepo}
}

func (s *DefaultProfileService) UpdateProfile(ctx context.Context, doctorID uuid.UUID, req dto.UpdateProfileRequest) (*dto.DoctorProfileDTO, error) {
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorID)
	if err != nil || doc == nil {
		return nil, errors.New("doctor profile not found")
	}

	if req.Gender != "" {
		doc.Gender = req.Gender
	}
	if req.ProfilePhoto != "" {
		doc.ProfilePhoto = req.ProfilePhoto
	}
	if req.Languages != "" {
		doc.Languages = req.Languages
	}
	if req.Biography != "" {
		doc.Biography = req.Biography
	}
	if req.DOB != "" {
		parsed, err := time.Parse("2006-01-02", req.DOB)
		if err == nil {
			doc.DOB = &parsed
		}
	}

	if err := s.doctorRepo.Update(ctx, doc); err != nil {
		return nil, err
	}

	return &dto.DoctorProfileDTO{
		PublicID:       doc.PublicID,
		FirstName:      doc.FirstName,
		LastName:       doc.LastName,
		Email:          doc.Email,
		Mobile:         doc.Mobile,
		Status:         string(doc.Status),
		MobileVerified: doc.MobileVerified,
		EmailVerified:  doc.EmailVerified,
	}, nil
}

func (s *DefaultProfileService) GetProfile(ctx context.Context, doctorID uuid.UUID) (*dto.DoctorProfileDTO, error) {
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorID)
	if err != nil || doc == nil {
		return nil, errors.New("doctor profile not found")
	}

	return &dto.DoctorProfileDTO{
		PublicID:       doc.PublicID,
		FirstName:      doc.FirstName,
		LastName:       doc.LastName,
		Email:          doc.Email,
		Mobile:         doc.Mobile,
		Status:         string(doc.Status),
		MobileVerified: doc.MobileVerified,
		EmailVerified:  doc.EmailVerified,
	}, nil
}
