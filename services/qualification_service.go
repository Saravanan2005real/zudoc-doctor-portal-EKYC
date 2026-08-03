package services

import (
	"context"
	"errors"

	"doctor-service/dto"
	"doctor-service/entities"
	"doctor-service/repositories"

	"github.com/google/uuid"
)

type QualificationService interface {
	AddQualification(ctx context.Context, doctorID uuid.UUID, req dto.AddQualificationRequest) (*dto.QualificationResponse, error)
	GetQualifications(ctx context.Context, doctorID uuid.UUID) ([]dto.QualificationResponse, error)
	DeleteQualification(ctx context.Context, qualificationID, doctorID uuid.UUID) error
}

type DefaultQualificationService struct {
	doctorRepo repositories.DoctorRepository
	qualRepo   repositories.QualificationRepository
}

func NewQualificationService(doctorRepo repositories.DoctorRepository, qualRepo repositories.QualificationRepository) QualificationService {
	return &DefaultQualificationService{doctorRepo: doctorRepo, qualRepo: qualRepo}
}

func (s *DefaultQualificationService) AddQualification(ctx context.Context, doctorID uuid.UUID, req dto.AddQualificationRequest) (*dto.QualificationResponse, error) {
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorID)
	if err != nil || doc == nil {
		return nil, errors.New("doctor not found")
	}

	qual := &entities.DoctorQualification{
		DoctorID:       doc.ID,
		Degree:         req.Degree,
		Specialization: req.Specialization,
		College:        req.College,
		University:     req.University,
		YearCompleted:  req.YearCompleted,
	}

	if err := s.qualRepo.Create(ctx, qual); err != nil {
		return nil, err
	}

	return &dto.QualificationResponse{
		QualificationID: qual.QualificationID,
		Degree:          qual.Degree,
		Specialization:  qual.Specialization,
		College:         qual.College,
		University:      qual.University,
		YearCompleted:   qual.YearCompleted,
		CreatedAt:       qual.CreatedAt,
	}, nil
}

func (s *DefaultQualificationService) GetQualifications(ctx context.Context, doctorID uuid.UUID) ([]dto.QualificationResponse, error) {
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorID)
	if err != nil || doc == nil {
		return nil, errors.New("doctor not found")
	}

	quals, err := s.qualRepo.FindByDoctorID(ctx, doc.ID)
	if err != nil {
		return nil, err
	}

	var res []dto.QualificationResponse
	for _, q := range quals {
		res = append(res, dto.QualificationResponse{
			QualificationID: q.QualificationID,
			Degree:          q.Degree,
			Specialization:  q.Specialization,
			College:         q.College,
			University:      q.University,
			YearCompleted:   q.YearCompleted,
			CreatedAt:       q.CreatedAt,
		})
	}
	return res, nil
}

func (s *DefaultQualificationService) DeleteQualification(ctx context.Context, qualificationID, doctorID uuid.UUID) error {
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorID)
	if err != nil || doc == nil {
		return errors.New("doctor not found")
	}
	return s.qualRepo.Delete(ctx, qualificationID, doc.ID)
}
