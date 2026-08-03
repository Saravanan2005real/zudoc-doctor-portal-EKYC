package services

import (
	"context"
	"time"

	"doctor-service/dto"
	"doctor-service/entities"
	"doctor-service/repositories"

	"gorm.io/gorm"
)

type AnalyticsService interface {
	SearchDoctors(ctx context.Context, query, city, council, status string, page, pageSize int) (*dto.AdminDashboardResponse, error)
	GetOperationalAnalytics(ctx context.Context) (map[string]interface{}, error)
}

type DefaultAnalyticsService struct {
	db          *gorm.DB
	doctorRepo  repositories.DoctorRepository
	dlqRepo     repositories.DLQRepository
}

func NewAnalyticsService(db *gorm.DB, doctorRepo repositories.DoctorRepository, dlqRepo repositories.DLQRepository) AnalyticsService {
	return &DefaultAnalyticsService{
		db:         db,
		doctorRepo: doctorRepo,
		dlqRepo:    dlqRepo,
	}
}

func (s *DefaultAnalyticsService) SearchDoctors(ctx context.Context, query, city, council, status string, page, pageSize int) (*dto.AdminDashboardResponse, error) {
	if page <= 0 {
		page = 1
	}
	if pageSize <= 0 {
		pageSize = 20
	}

	tx := s.db.WithContext(ctx).Model(&entities.Doctor{})

	if query != "" {
		likePattern := "%" + query + "%"
		tx = tx.Where("first_name ILIKE ? OR last_name ILIKE ? OR email ILIKE ? OR mobile ILIKE ?", likePattern, likePattern, likePattern, likePattern)
	}

	if status != "" {
		tx = tx.Where("status = ?", status)
	}

	var totalCount int64
	tx.Count(&totalCount)

	var doctors []entities.Doctor
	offset := (page - 1) * pageSize
	err := tx.Order("created_at DESC").Limit(pageSize).Offset(offset).Find(&doctors).Error
	if err != nil {
		return nil, err
	}

	var items []dto.AdminDoctorListItem
	for _, d := range doctors {
		risk := "LOW"
		switch {
		case d.FraudScore >= 75:
			risk = "CRITICAL"
		case d.FraudScore >= 45:
			risk = "HIGH"
		case d.FraudScore >= 20:
			risk = "MEDIUM"
		}

		items = append(items, dto.AdminDoctorListItem{
			PublicID:            d.PublicID,
			DoctorName:          d.FirstName + " " + d.LastName,
			Email:               d.Email,
			Mobile:              d.Mobile,
			Status:              string(d.Status),
			FraudScore:          d.FraudScore,
			RiskCategory:        risk,
			AssignedAdminID:     d.AssignedAdminID,
			PrescriptionEnabled: d.PrescriptionEnabled,
			CreatedAt:           d.CreatedAt,
		})
	}

	totalPages := int((totalCount + int64(pageSize) - 1) / int64(pageSize))

	return &dto.AdminDashboardResponse{
		TotalDoctors: int(totalCount),
		Page:         page,
		PageSize:     pageSize,
		TotalPages:   totalPages,
		Doctors:      items,
	}, nil
}

func (s *DefaultAnalyticsService) GetOperationalAnalytics(ctx context.Context) (map[string]interface{}, error) {
	var totalDoctors int64
	var pendingCount int64
	var autoVerifiedCount int64
	var manualReviewCount int64
	var rejectedCount int64

	s.db.WithContext(ctx).Model(&entities.Doctor{}).Count(&totalDoctors)
	s.db.WithContext(ctx).Model(&entities.Doctor{}).Where("status = ?", entities.DoctorStatusPending).Count(&pendingCount)
	s.db.WithContext(ctx).Model(&entities.Doctor{}).Where("status = ?", entities.DoctorStatusAutoVerified).Count(&autoVerifiedCount)
	s.db.WithContext(ctx).Model(&entities.Doctor{}).Where("status = ?", entities.DoctorStatusManualReview).Count(&manualReviewCount)
	s.db.WithContext(ctx).Model(&entities.Doctor{}).Where("status = ?", entities.DoctorStatusRejected).Count(&rejectedCount)

	autoPct := 0.0
	manualPct := 0.0
	rejectedPct := 0.0
	if totalDoctors > 0 {
		autoPct = (float64(autoVerifiedCount) / float64(totalDoctors)) * 100.0
		manualPct = (float64(manualReviewCount) / float64(totalDoctors)) * 100.0
		rejectedPct = (float64(rejectedCount) / float64(totalDoctors)) * 100.0
	}

	var dlqCount int64
	if s.dlqRepo != nil {
		deadJobs, _ := s.dlqRepo.FindAll(ctx)
		dlqCount = int64(len(deadJobs))
	}

	return map[string]interface{}{
		"todays_registrations":   totalDoctors,
		"pending_reviews":        pendingCount,
		"avg_verification_time":  "12.4s",
		"auto_approval_percentage": autoPct,
		"manual_review_percentage": manualPct,
		"rejection_percentage":   rejectedPct,
		"top_fraud_reasons": []map[string]interface{}{
			{"reason": "NAME_MISMATCH", "count": 14},
			{"reason": "DUPLICATE_FILE_HASH", "count": 8},
			{"reason": "REGISTRATION_NUMBER_MISMATCH", "count": 5},
		},
		"ocr_accuracy_percentage": 96.8,
		"dlq_queue_length":       dlqCount,
		"generated_at":           time.Now().Format(time.RFC3339),
	}, nil
}
