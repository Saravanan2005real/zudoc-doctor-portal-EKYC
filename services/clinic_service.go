package services

import (
	"context"

	"doctor-service/dto"
	"doctor-service/entities"
	"doctor-service/repositories"

	"github.com/google/uuid"
)

type ClinicService interface {
	AddClinic(ctx context.Context, doctorID uuid.UUID, req dto.AddClinicRequest) (*dto.ClinicResponse, error)
	GetClinics(ctx context.Context, doctorID uuid.UUID) ([]dto.ClinicResponse, error)
	DeleteClinic(ctx context.Context, clinicID, doctorID uuid.UUID) error
}

type DefaultClinicService struct {
	clinicRepo repositories.ClinicRepository
}

func NewClinicService(clinicRepo repositories.ClinicRepository) ClinicService {
	return &DefaultClinicService{clinicRepo: clinicRepo}
}

func (s *DefaultClinicService) AddClinic(ctx context.Context, doctorID uuid.UUID, req dto.AddClinicRequest) (*dto.ClinicResponse, error) {
	mode := entities.ConsultationMode(req.ConsultationMode)
	if mode == "" {
		mode = entities.ConsultationModeOffline
	}

	clinic := &entities.DoctorClinic{
		DoctorID:         doctorID,
		ClinicName:       req.ClinicName,
		Address:          req.Address,
		City:             req.City,
		State:            req.State,
		Pincode:          req.Pincode,
		Latitude:         req.Latitude,
		Longitude:        req.Longitude,
		ConsultationMode: mode,
		ConsultationFee:  req.ConsultationFee,
	}

	if err := s.clinicRepo.Create(ctx, clinic); err != nil {
		return nil, err
	}

	return &dto.ClinicResponse{
		ClinicID:         clinic.ClinicID,
		ClinicName:       clinic.ClinicName,
		Address:          clinic.Address,
		City:             clinic.City,
		State:            clinic.State,
		Pincode:          clinic.Pincode,
		ConsultationMode: string(clinic.ConsultationMode),
		ConsultationFee:  clinic.ConsultationFee,
		CreatedAt:        clinic.CreatedAt,
	}, nil
}

func (s *DefaultClinicService) GetClinics(ctx context.Context, doctorID uuid.UUID) ([]dto.ClinicResponse, error) {
	clinics, err := s.clinicRepo.FindByDoctorID(ctx, doctorID)
	if err != nil {
		return nil, err
	}

	var res []dto.ClinicResponse
	for _, c := range clinics {
		res = append(res, dto.ClinicResponse{
			ClinicID:         c.ClinicID,
			ClinicName:       c.ClinicName,
			Address:          c.Address,
			City:             c.City,
			State:            c.State,
			Pincode:          c.Pincode,
			ConsultationMode: string(c.ConsultationMode),
			ConsultationFee:  c.ConsultationFee,
			CreatedAt:        c.CreatedAt,
		})
	}
	return res, nil
}

func (s *DefaultClinicService) DeleteClinic(ctx context.Context, clinicID, doctorID uuid.UUID) error {
	return s.clinicRepo.Delete(ctx, clinicID, doctorID)
}
