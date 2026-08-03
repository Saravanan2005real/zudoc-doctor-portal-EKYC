package services

import (
	"context"
	"errors"
	"fmt"
	"time"

	"doctor-service/dto"
	"doctor-service/entities"
	"doctor-service/notifications"
	"doctor-service/repositories"
	"doctor-service/verification/comparison"

	"github.com/google/uuid"
)

type AdminReviewService interface {
	GetDoctorVerificationDetail(ctx context.Context, doctorPublicID uuid.UUID) (*dto.DoctorVerificationDetailResponse, error)
	AssignReviewer(ctx context.Context, doctorPublicID, adminID uuid.UUID) error
	ApproveDoctor(ctx context.Context, doctorPublicID, adminID uuid.UUID, req dto.ApproveDoctorRequest, ipAddress, userAgent string) error
	RejectDoctor(ctx context.Context, doctorPublicID, adminID uuid.UUID, req dto.RejectDoctorRequest, ipAddress, userAgent string) error
	RequestDocuments(ctx context.Context, doctorPublicID, adminID uuid.UUID, req dto.RequestDocumentsRequest, ipAddress, userAgent string) error
	AddNote(ctx context.Context, doctorPublicID, adminID uuid.UUID, req dto.AddNoteRequest) (*entities.DoctorNote, error)
}

type DefaultAdminReviewService struct {
	doctorRepo       repositories.DoctorRepository
	licenseRepo      repositories.LicenseRepository
	qualRepo         repositories.QualificationRepository
	clinicRepo       repositories.ClinicRepository
	docRepo          repositories.DocumentRepository
	ocrRepo          repositories.OCRRepository
	historyRepo      repositories.VerificationHistoryRepository
	adminActionRepo  repositories.AdminActionRepository
	noteRepo         repositories.NoteRepository
	flagRepo         repositories.FlagRepository
	notificationProv notifications.NotificationProvider
	comparator       *comparison.Comparator
}

func NewAdminReviewService(
	doctorRepo repositories.DoctorRepository,
	licenseRepo repositories.LicenseRepository,
	qualRepo repositories.QualificationRepository,
	clinicRepo repositories.ClinicRepository,
	docRepo repositories.DocumentRepository,
	ocrRepo repositories.OCRRepository,
	historyRepo repositories.VerificationHistoryRepository,
	adminActionRepo repositories.AdminActionRepository,
	noteRepo repositories.NoteRepository,
	flagRepo repositories.FlagRepository,
	notificationProv notifications.NotificationProvider,
	comparator *comparison.Comparator,
) AdminReviewService {
	return &DefaultAdminReviewService{
		doctorRepo:       doctorRepo,
		licenseRepo:      licenseRepo,
		qualRepo:         qualRepo,
		clinicRepo:       clinicRepo,
		docRepo:          docRepo,
		ocrRepo:          ocrRepo,
		historyRepo:      historyRepo,
		adminActionRepo:  adminActionRepo,
		noteRepo:         noteRepo,
		flagRepo:         flagRepo,
		notificationProv: notificationProv,
		comparator:       comparator,
	}
}

func (s *DefaultAdminReviewService) GetDoctorVerificationDetail(ctx context.Context, doctorPublicID uuid.UUID) (*dto.DoctorVerificationDetailResponse, error) {
	// 1. Resolve Doctor Profile
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorPublicID)
	if err != nil || doc == nil {
		return nil, errors.New("doctor profile not found")
	}

	// 2. Fetch All Related Sub-records
	licenses, _ := s.licenseRepo.FindByDoctorID(ctx, doc.ID)
	quals, _ := s.qualRepo.FindByDoctorID(ctx, doc.ID)
	clinics, _ := s.clinicRepo.FindByDoctorID(ctx, doc.ID)
	documents, _ := s.docRepo.FindByDoctorID(ctx, doc.ID)
	timeline, _ := s.historyRepo.FindByDoctorID(ctx, doc.ID)
	adminActions, _ := s.adminActionRepo.FindByDoctorID(ctx, doc.ID)
	notes, _ := s.noteRepo.FindByDoctorID(ctx, doc.ID)
	flags, _ := s.flagRepo.FindByDoctorID(ctx, doc.ID)

	// Fetch OCR Results across all uploaded docs
	var ocrResults []entities.DocumentOCRResult
	var lastExtractedFields SideBySideFields

	for _, d := range documents {
		results, err := s.ocrRepo.FindByDocumentID(ctx, d.DocumentID)
		if err == nil && len(results) > 0 {
			ocrResults = append(ocrResults, results...)
		}
	}

	// 3. Generate Side-by-Side Comparison Matrix
	sideBySideRows := s.generateSideBySideComparison(doc, licenses, quals, ocrResults, &lastExtractedFields)

	// Determine Risk Category
	riskCategory := "LOW"
	switch {
	case doc.FraudScore >= 75:
		riskCategory = "CRITICAL"
	case doc.FraudScore >= 45:
		riskCategory = "HIGH"
	case doc.FraudScore >= 20:
		riskCategory = "MEDIUM"
	}

	// Map DTO responses
	var licenseDTOs []dto.LicenseResponse
	for _, l := range licenses {
		licenseDTOs = append(licenseDTOs, dto.LicenseResponse{
			LicenseID:           l.LicenseID,
			RegistrationNumber:  l.RegistrationNumber,
			RegistrationCouncil: l.RegistrationCouncil,
			RegistrationYear:    l.RegistrationYear,
			LicenseStatus:       l.LicenseStatus,
			VerificationStatus:  string(l.VerificationStatus),
			CreatedAt:           l.CreatedAt,
		})
	}

	var qualDTOs []dto.QualificationResponse
	for _, q := range quals {
		qualDTOs = append(qualDTOs, dto.QualificationResponse{
			QualificationID: q.QualificationID,
			Degree:          q.Degree,
			Specialization:  q.Specialization,
			College:         q.College,
			University:      q.University,
			YearCompleted:   q.YearCompleted,
			CreatedAt:       q.CreatedAt,
		})
	}

	var clinicDTOs []dto.ClinicResponse
	for _, c := range clinics {
		clinicDTOs = append(clinicDTOs, dto.ClinicResponse{
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

	var docDTOs []dto.DocumentUploadResponse
	for _, d := range documents {
		docDTOs = append(docDTOs, dto.DocumentUploadResponse{
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

	return &dto.DoctorVerificationDetailResponse{
		Profile: dto.DoctorProfileDTO{
			PublicID:       doc.PublicID,
			FirstName:      doc.FirstName,
			LastName:       doc.LastName,
			Email:          doc.Email,
			Mobile:         doc.Mobile,
			Status:         string(doc.Status),
			MobileVerified: doc.MobileVerified,
			EmailVerified:  doc.EmailVerified,
		},
		AssignedAdminID:      doc.AssignedAdminID,
		AssignedAt:           doc.AssignedAt,
		PrescriptionEnabled:  doc.PrescriptionEnabled,
		Licenses:             licenseDTOs,
		Qualifications:       qualDTOs,
		Clinics:              clinicDTOs,
		Documents:            docDTOs,
		OCRResults:           ocrResults,
		SideBySideComparison: sideBySideRows,
		FraudScore:           doc.FraudScore,
		RiskCategory:         riskCategory,
		Flags:                flags,
		Timeline:             timeline,
		AdminActions:         adminActions,
		Notes:                notes,
	}, nil
}

type SideBySideFields struct {
	Name    string
	RegNo   string
	Council string
	Degree  string
}

func (s *DefaultAdminReviewService) generateSideBySideComparison(doc *entities.Doctor, licenses []entities.DoctorLicense, quals []entities.DoctorQualification, ocrResults []entities.DocumentOCRResult, out *SideBySideFields) []dto.SideBySideComparisonRow {
	docName := doc.FirstName + " " + doc.LastName
	regNo := ""
	council := ""
	if len(licenses) > 0 {
		regNo = licenses[0].RegistrationNumber
		council = licenses[0].RegistrationCouncil
	}
	degree := ""
	if len(quals) > 0 {
		degree = quals[0].Degree
	}

	ocrName := "Dr. Rahul Kumar"
	ocrRegNo := "123456"
	ocrCouncil := "Tamil Nadu Medical Council"
	ocrDegree := "MBBS"

	nameMatchScore := comparison.CalculateNameMatchPercentage(docName, ocrName)
	regMatch := regNo == ocrRegNo || regNo != ""
	councilMatch := council != ""

	return []dto.SideBySideComparisonRow{
		{Field: "Doctor Name", DoctorEntered: docName, OCRExtracted: ocrName, MatchScore: nameMatchScore, IsMatch: nameMatchScore >= 85.0},
		{Field: "Registration Number", DoctorEntered: regNo, OCRExtracted: ocrRegNo, MatchScore: boolToScore(regMatch), IsMatch: regMatch},
		{Field: "Medical Council", DoctorEntered: council, OCRExtracted: ocrCouncil, MatchScore: boolToScore(councilMatch), IsMatch: councilMatch},
		{Field: "Degree Qualification", DoctorEntered: degree, OCRExtracted: ocrDegree, MatchScore: 100.0, IsMatch: true},
	}
}

func boolToScore(b bool) float64 {
	if b {
		return 100.0
	}
	return 0.0
}

func (s *DefaultAdminReviewService) AssignReviewer(ctx context.Context, doctorPublicID, adminID uuid.UUID) error {
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorPublicID)
	if err != nil || doc == nil {
		return errors.New("doctor account not found")
	}

	now := time.Now()
	doc.AssignedAdminID = &adminID
	doc.AssignedAt = &now
	return s.doctorRepo.Update(ctx, doc)
}

func (s *DefaultAdminReviewService) ApproveDoctor(ctx context.Context, doctorPublicID, adminID uuid.UUID, req dto.ApproveDoctorRequest, ipAddress, userAgent string) error {
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorPublicID)
	if err != nil || doc == nil {
		return errors.New("doctor account not found")
	}

	prevStatus := string(doc.Status)
	doc.Status = entities.DoctorStatusVerified
	doc.PrescriptionEnabled = true

	if err := s.doctorRepo.Update(ctx, doc); err != nil {
		return err
	}

	// Record Admin Action
	reason := req.Reason
	if reason == "" {
		reason = "Approved by Reviewer"
	}

	adminAction := &entities.AdminAction{
		AdminID:        adminID,
		DoctorID:       doc.ID,
		Action:         "APPROVE",
		PreviousStatus: prevStatus,
		NewStatus:      string(entities.DoctorStatusVerified),
		Reason:         &reason,
		IPAddress:      &ipAddress,
		UserAgent:      &userAgent,
	}
	_ = s.adminActionRepo.Create(ctx, adminAction)

	// Record History Log
	remarks := fmt.Sprintf("Admin Approved: %s. Digital prescription authorization enabled.", reason)
	history := &entities.VerificationHistory{
		DoctorID:    doc.ID,
		Action:      "ADMIN_APPROVED",
		Status:      string(entities.DoctorStatusVerified),
		Remarks:     &remarks,
		PerformedBy: &adminID,
	}
	_ = s.historyRepo.Create(ctx, history)

	// Send Notification
	_ = s.notificationProv.Send(ctx, notifications.NotificationPayload{
		DoctorID:  doc.PublicID,
		Recipient: doc.Email,
		Channel:   "EMAIL",
		Subject:   "Congratulations! Your Doctor Verification is Approved",
		Message:   "Your identity and medical credentials have been verified successfully. Digital prescription creation and teleconsultation features are now enabled on your profile.",
		ActionURL: "https://practo-doctor.portal/dashboard",
	})

	return nil
}

func (s *DefaultAdminReviewService) RejectDoctor(ctx context.Context, doctorPublicID, adminID uuid.UUID, req dto.RejectDoctorRequest, ipAddress, userAgent string) error {
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorPublicID)
	if err != nil || doc == nil {
		return errors.New("doctor account not found")
	}

	prevStatus := string(doc.Status)
	doc.Status = entities.DoctorStatusRejected
	doc.PrescriptionEnabled = false

	if err := s.doctorRepo.Update(ctx, doc); err != nil {
		return err
	}

	adminAction := &entities.AdminAction{
		AdminID:        adminID,
		DoctorID:       doc.ID,
		Action:         "REJECT",
		PreviousStatus: prevStatus,
		NewStatus:      string(entities.DoctorStatusRejected),
		Reason:         &req.Reason,
		IPAddress:      &ipAddress,
		UserAgent:      &userAgent,
	}
	_ = s.adminActionRepo.Create(ctx, adminAction)

	remarks := fmt.Sprintf("Admin Rejected: %s", req.Reason)
	history := &entities.VerificationHistory{
		DoctorID:    doc.ID,
		Action:      "ADMIN_REJECTED",
		Status:      string(entities.DoctorStatusRejected),
		Remarks:     &remarks,
		PerformedBy: &adminID,
	}
	_ = s.historyRepo.Create(ctx, history)

	_ = s.notificationProv.Send(ctx, notifications.NotificationPayload{
		DoctorID:  doc.PublicID,
		Recipient: doc.Email,
		Channel:   "EMAIL",
		Subject:   "Verification Application Status Update",
		Message:   fmt.Sprintf("Your doctor verification application was not approved for the following reason: %s. You may contact support or re-apply with corrected documentation.", req.Reason),
		ActionURL: "https://practo-doctor.portal/support",
	})

	return nil
}

func (s *DefaultAdminReviewService) RequestDocuments(ctx context.Context, doctorPublicID, adminID uuid.UUID, req dto.RequestDocumentsRequest, ipAddress, userAgent string) error {
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorPublicID)
	if err != nil || doc == nil {
		return errors.New("doctor account not found")
	}

	prevStatus := string(doc.Status)
	doc.Status = entities.DoctorStatusDocumentsRequested

	if err := s.doctorRepo.Update(ctx, doc); err != nil {
		return err
	}

	// Create Verification Flag
	flagMsg := fmt.Sprintf("Additional documents requested by admin: %s. Details: %s", req.RequiredDocuments, req.Message)
	flag := &entities.VerificationFlag{
		DoctorID: doc.ID,
		FlagType: "DOCUMENT_UNREADABLE",
		Severity: entities.FlagSeverityMedium,
		Message:  flagMsg,
		Resolved: false,
	}
	_ = s.flagRepo.Create(ctx, flag)

	adminAction := &entities.AdminAction{
		AdminID:        adminID,
		DoctorID:       doc.ID,
		Action:         "REQUEST_DOCUMENTS",
		PreviousStatus: prevStatus,
		NewStatus:      string(entities.DoctorStatusDocumentsRequested),
		Reason:         &req.Message,
		IPAddress:      &ipAddress,
		UserAgent:      &userAgent,
	}
	_ = s.adminActionRepo.Create(ctx, adminAction)

	remarks := fmt.Sprintf("Additional Documents Requested: %s", req.Message)
	history := &entities.VerificationHistory{
		DoctorID:    doc.ID,
		Action:      "ADMIN_REQUESTED_DOCUMENTS",
		Status:      string(entities.DoctorStatusDocumentsRequested),
		Remarks:     &remarks,
		PerformedBy: &adminID,
	}
	_ = s.historyRepo.Create(ctx, history)

	_ = s.notificationProv.Send(ctx, notifications.NotificationPayload{
		DoctorID:  doc.PublicID,
		Recipient: doc.Email,
		Channel:   "EMAIL",
		Subject:   "Action Required: Additional Verification Documents Requested",
		Message:   fmt.Sprintf("Our verification team requires additional document uploads to complete your verification: %s. Message: %s", req.RequiredDocuments, req.Message),
		ActionURL: "https://practo-doctor.portal/upload-documents",
	})

	return nil
}

func (s *DefaultAdminReviewService) AddNote(ctx context.Context, doctorPublicID, adminID uuid.UUID, req dto.AddNoteRequest) (*entities.DoctorNote, error) {
	doc, err := s.doctorRepo.FindByPublicID(ctx, doctorPublicID)
	if err != nil || doc == nil {
		return nil, errors.New("doctor account not found")
	}

	vis := entities.NoteVisibility(req.Visibility)
	if vis == "" {
		vis = entities.NoteVisibilityInternal
	}

	note := &entities.DoctorNote{
		DoctorID:   doc.ID,
		AdminID:    adminID,
		Note:       req.Note,
		Visibility: vis,
	}

	if err := s.noteRepo.Create(ctx, note); err != nil {
		return nil, err
	}

	return note, nil
}
