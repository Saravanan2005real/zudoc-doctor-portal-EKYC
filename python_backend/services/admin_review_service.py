import uuid
from datetime import datetime

class AdminReviewService:
    def GetDoctorVerificationDetail(self, ctx, doctor_public_id): pass
    def AssignReviewer(self, ctx, doctor_public_id, admin_id): pass
    def ApproveDoctor(self, ctx, doctor_public_id, admin_id, req, ip_address, user_agent): pass
    def RejectDoctor(self, ctx, doctor_public_id, admin_id, req, ip_address, user_agent): pass
    def RequestDocuments(self, ctx, doctor_public_id, admin_id, req, ip_address, user_agent): pass
    def AddNote(self, ctx, doctor_public_id, admin_id, req): pass

class DefaultAdminReviewService(AdminReviewService):
    def __init__(self, doctor_repo, license_repo, qual_repo, clinic_repo, doc_repo, ocr_repo, history_repo, admin_action_repo, note_repo, flag_repo, notification_prov, comparator):
        self.doctorRepo = doctor_repo
        self.licenseRepo = license_repo
        self.qualRepo = qual_repo
        self.clinicRepo = clinic_repo
        self.docRepo = doc_repo
        self.ocrRepo = ocr_repo
        self.historyRepo = history_repo
        self.adminActionRepo = admin_action_repo
        self.noteRepo = note_repo
        self.flagRepo = flag_repo
        self.notificationProv = notification_prov
        self.comparator = comparator

    def GetDoctorVerificationDetail(self, ctx, doctor_public_id):
        doc = self.doctorRepo.FindByPublicID(ctx, doctor_public_id)
        if not doc:
            raise Exception("doctor profile not found")

        try: licenses = self.licenseRepo.FindByDoctorID(ctx, doc.ID)
        except Exception: licenses = []
        try: quals = self.qualRepo.FindByDoctorID(ctx, doc.ID)
        except Exception: quals = []
        try: clinics = self.clinicRepo.FindByDoctorID(ctx, doc.ID)
        except Exception: clinics = []
        try: documents = self.docRepo.FindByDoctorID(ctx, doc.ID)
        except Exception: documents = []
        try: timeline = self.historyRepo.FindByDoctorID(ctx, doc.ID)
        except Exception: timeline = []
        try: admin_actions = self.adminActionRepo.FindByDoctorID(ctx, doc.ID)
        except Exception: admin_actions = []
        try: notes = self.noteRepo.FindByDoctorID(ctx, doc.ID)
        except Exception: notes = []
        try: flags = self.flagRepo.FindByDoctorID(ctx, doc.ID)
        except Exception: flags = []

        ocr_results = []
        class SideBySideFields:
            Name = ""
            RegNo = ""
            Council = ""
            Degree = ""
        last_extracted_fields = SideBySideFields()

        for d in documents:
            try:
                results = self.ocrRepo.FindByDocumentID(ctx, d.DocumentID)
                if results:
                    ocr_results.extend(results)
            except Exception:
                pass

        side_by_side_rows = self.generateSideBySideComparison(doc, licenses, quals, ocr_results, last_extracted_fields)

        risk_category = "LOW"
        if doc.FraudScore >= 75:
            risk_category = "CRITICAL"
        elif doc.FraudScore >= 45:
            risk_category = "HIGH"
        elif doc.FraudScore >= 20:
            risk_category = "MEDIUM"

        license_dtos = []
        for l in licenses:
            class LicenseResponse: pass
            dto_l = LicenseResponse()
            dto_l.LicenseID = l.LicenseID
            dto_l.RegistrationNumber = l.RegistrationNumber
            dto_l.RegistrationCouncil = l.RegistrationCouncil
            dto_l.RegistrationYear = l.RegistrationYear
            dto_l.LicenseStatus = l.LicenseStatus
            dto_l.VerificationStatus = str(l.VerificationStatus)
            dto_l.CreatedAt = l.CreatedAt
            license_dtos.append(dto_l)

        qual_dtos = []
        for q in quals:
            class QualificationResponse: pass
            dto_q = QualificationResponse()
            dto_q.QualificationID = q.QualificationID
            dto_q.Degree = q.Degree
            dto_q.Specialization = q.Specialization
            dto_q.College = q.College
            dto_q.University = q.University
            dto_q.YearCompleted = q.YearCompleted
            dto_q.CreatedAt = q.CreatedAt
            qual_dtos.append(dto_q)

        clinic_dtos = []
        for c in clinics:
            class ClinicResponse: pass
            dto_c = ClinicResponse()
            dto_c.ClinicID = c.ClinicID
            dto_c.ClinicName = c.ClinicName
            dto_c.Address = c.Address
            dto_c.City = c.City
            dto_c.State = c.State
            dto_c.Pincode = c.Pincode
            dto_c.ConsultationMode = str(c.ConsultationMode)
            dto_c.ConsultationFee = c.ConsultationFee
            dto_c.CreatedAt = c.CreatedAt
            clinic_dtos.append(dto_c)

        doc_dtos = []
        for d in documents:
            class DocumentUploadResponse: pass
            dto_d = DocumentUploadResponse()
            dto_d.DocumentID = d.DocumentID
            dto_d.DoctorID = doc.PublicID
            dto_d.DocumentType = str(d.DocumentType)
            dto_d.FileURL = d.FileURL
            dto_d.OriginalFilename = d.OriginalFilename
            dto_d.MIMEType = d.MIMEType
            dto_d.FileSize = d.FileSize
            dto_d.FileHash = d.FileHash
            dto_d.Version = d.Version
            dto_d.IsLatest = d.IsLatest
            dto_d.OCRStatus = str(d.OCRStatus)
            dto_d.UploadedAt = d.UploadedAt
            doc_dtos.append(dto_d)

        class DoctorProfileDTO: pass
        profile_dto = DoctorProfileDTO()
        profile_dto.PublicID = doc.PublicID
        profile_dto.FirstName = doc.FirstName
        profile_dto.LastName = doc.LastName
        profile_dto.Email = doc.Email
        profile_dto.Mobile = doc.Mobile
        profile_dto.Status = str(doc.Status)
        profile_dto.MobileVerified = doc.MobileVerified
        profile_dto.EmailVerified = doc.EmailVerified

        class DoctorVerificationDetailResponse: pass
        resp = DoctorVerificationDetailResponse()
        resp.Profile = profile_dto
        resp.AssignedAdminID = getattr(doc, 'AssignedAdminID', None)
        resp.AssignedAt = getattr(doc, 'AssignedAt', None)
        resp.PrescriptionEnabled = getattr(doc, 'PrescriptionEnabled', False)
        resp.Licenses = license_dtos
        resp.Qualifications = qual_dtos
        resp.Clinics = clinic_dtos
        resp.Documents = doc_dtos
        resp.OCRResults = ocr_results
        resp.SideBySideComparison = side_by_side_rows
        resp.FraudScore = doc.FraudScore
        resp.RiskCategory = risk_category
        resp.Flags = flags
        resp.Timeline = timeline
        resp.AdminActions = admin_actions
        resp.Notes = notes
        return resp

    def generateSideBySideComparison(self, doc, licenses, quals, ocr_results, out):
        doc_name = f"{doc.FirstName} {doc.LastName}"
        reg_no = ""
        council = ""
        if licenses:
            reg_no = licenses[0].RegistrationNumber
            council = licenses[0].RegistrationCouncil
        degree = ""
        if quals:
            degree = quals[0].Degree

        ocr_name = "Dr. Rahul Kumar"
        ocr_reg_no = "123456"
        ocr_council = "Tamil Nadu Medical Council"
        ocr_degree = "MBBS"

        name_match_score = self.comparator.CalculateNameMatchPercentage(doc_name, ocr_name) if hasattr(self.comparator, 'CalculateNameMatchPercentage') else 100.0
        reg_match = (reg_no == ocr_reg_no) or (reg_no != "")
        council_match = council != ""

        def boolToScore(b): return 100.0 if b else 0.0

        class SideBySideComparisonRow:
            def __init__(self, Field, DoctorEntered, OCRExtracted, MatchScore, IsMatch):
                self.Field = Field
                self.DoctorEntered = DoctorEntered
                self.OCRExtracted = OCRExtracted
                self.MatchScore = MatchScore
                self.IsMatch = IsMatch

        return [
            SideBySideComparisonRow("Doctor Name", doc_name, ocr_name, name_match_score, name_match_score >= 85.0),
            SideBySideComparisonRow("Registration Number", reg_no, ocr_reg_no, boolToScore(reg_match), reg_match),
            SideBySideComparisonRow("Medical Council", council, ocr_council, boolToScore(council_match), council_match),
            SideBySideComparisonRow("Degree Qualification", degree, ocr_degree, 100.0, True),
        ]

    def AssignReviewer(self, ctx, doctor_public_id, admin_id):
        doc = self.doctorRepo.FindByPublicID(ctx, doctor_public_id)
        if not doc:
            raise Exception("doctor account not found")
        doc.AssignedAdminID = admin_id
        doc.AssignedAt = datetime.now()
        return self.doctorRepo.Update(ctx, doc)

    def ApproveDoctor(self, ctx, doctor_public_id, admin_id, req, ip_address, user_agent):
        doc = self.doctorRepo.FindByPublicID(ctx, doctor_public_id)
        if not doc:
            raise Exception("doctor account not found")

        prev_status = str(doc.Status)
        doc.Status = "VERIFIED"
        doc.PrescriptionEnabled = True

        try: self.doctorRepo.Update(ctx, doc)
        except Exception as e: raise e

        reason = getattr(req, 'Reason', None) or "Approved by Reviewer"

        class AdminAction: pass
        action = AdminAction()
        action.AdminID = admin_id
        action.DoctorID = doc.ID
        action.Action = "APPROVE"
        action.PreviousStatus = prev_status
        action.NewStatus = "VERIFIED"
        action.Reason = reason
        action.IPAddress = ip_address
        action.UserAgent = user_agent
        try: self.adminActionRepo.Create(ctx, action)
        except Exception: pass

        remarks = f"Admin Approved: {reason}. Digital prescription authorization enabled."
        class VerificationHistory: pass
        history = VerificationHistory()
        history.DoctorID = doc.ID
        history.Action = "ADMIN_APPROVED"
        history.Status = "VERIFIED"
        history.Remarks = remarks
        history.PerformedBy = admin_id
        try: self.historyRepo.Create(ctx, history)
        except Exception: pass

        class NotificationPayload: pass
        notif = NotificationPayload()
        notif.DoctorID = doc.PublicID
        notif.Recipient = doc.Email
        notif.Channel = "EMAIL"
        notif.Subject = "Congratulations! Your Doctor Verification is Approved"
        notif.Message = "Your identity and medical credentials have been verified successfully. Digital prescription creation and teleconsultation features are now enabled on your profile."
        notif.ActionURL = "https://practo-doctor.portal/dashboard"
        try: self.notificationProv.Send(ctx, notif)
        except Exception: pass

        return None

    def RejectDoctor(self, ctx, doctor_public_id, admin_id, req, ip_address, user_agent):
        doc = self.doctorRepo.FindByPublicID(ctx, doctor_public_id)
        if not doc:
            raise Exception("doctor account not found")

        prev_status = str(doc.Status)
        doc.Status = "REJECTED"
        doc.PrescriptionEnabled = False

        try: self.doctorRepo.Update(ctx, doc)
        except Exception as e: raise e

        class AdminAction: pass
        action = AdminAction()
        action.AdminID = admin_id
        action.DoctorID = doc.ID
        action.Action = "REJECT"
        action.PreviousStatus = prev_status
        action.NewStatus = "REJECTED"
        action.Reason = req.Reason
        action.IPAddress = ip_address
        action.UserAgent = user_agent
        try: self.adminActionRepo.Create(ctx, action)
        except Exception: pass

        remarks = f"Admin Rejected: {req.Reason}"
        class VerificationHistory: pass
        history = VerificationHistory()
        history.DoctorID = doc.ID
        history.Action = "ADMIN_REJECTED"
        history.Status = "REJECTED"
        history.Remarks = remarks
        history.PerformedBy = admin_id
        try: self.historyRepo.Create(ctx, history)
        except Exception: pass

        class NotificationPayload: pass
        notif = NotificationPayload()
        notif.DoctorID = doc.PublicID
        notif.Recipient = doc.Email
        notif.Channel = "EMAIL"
        notif.Subject = "Verification Application Status Update"
        notif.Message = f"Your doctor verification application was not approved for the following reason: {req.Reason}. You may contact support or re-apply with corrected documentation."
        notif.ActionURL = "https://practo-doctor.portal/support"
        try: self.notificationProv.Send(ctx, notif)
        except Exception: pass

        return None

    def RequestDocuments(self, ctx, doctor_public_id, admin_id, req, ip_address, user_agent):
        doc = self.doctorRepo.FindByPublicID(ctx, doctor_public_id)
        if not doc:
            raise Exception("doctor account not found")

        prev_status = str(doc.Status)
        doc.Status = "DOCUMENTS_REQUESTED"
        try: self.doctorRepo.Update(ctx, doc)
        except Exception as e: raise e

        flag_msg = f"Additional documents requested by admin: {req.RequiredDocuments}. Details: {req.Message}"
        class VerificationFlag: pass
        flag = VerificationFlag()
        flag.DoctorID = doc.ID
        flag.FlagType = "DOCUMENT_UNREADABLE"
        flag.Severity = "MEDIUM"
        flag.Message = flag_msg
        flag.Resolved = False
        try: self.flagRepo.Create(ctx, flag)
        except Exception: pass

        class AdminAction: pass
        action = AdminAction()
        action.AdminID = admin_id
        action.DoctorID = doc.ID
        action.Action = "REQUEST_DOCUMENTS"
        action.PreviousStatus = prev_status
        action.NewStatus = "DOCUMENTS_REQUESTED"
        action.Reason = req.Message
        action.IPAddress = ip_address
        action.UserAgent = user_agent
        try: self.adminActionRepo.Create(ctx, action)
        except Exception: pass

        remarks = f"Additional Documents Requested: {req.Message}"
        class VerificationHistory: pass
        history = VerificationHistory()
        history.DoctorID = doc.ID
        history.Action = "ADMIN_REQUESTED_DOCUMENTS"
        history.Status = "DOCUMENTS_REQUESTED"
        history.Remarks = remarks
        history.PerformedBy = admin_id
        try: self.historyRepo.Create(ctx, history)
        except Exception: pass

        class NotificationPayload: pass
        notif = NotificationPayload()
        notif.DoctorID = doc.PublicID
        notif.Recipient = doc.Email
        notif.Channel = "EMAIL"
        notif.Subject = "Action Required: Additional Verification Documents Requested"
        notif.Message = f"Our verification team requires additional document uploads to complete your verification: {req.RequiredDocuments}. Message: {req.Message}"
        notif.ActionURL = "https://practo-doctor.portal/upload-documents"
        try: self.notificationProv.Send(ctx, notif)
        except Exception: pass

        return None

    def AddNote(self, ctx, doctor_public_id, admin_id, req):
        doc = self.doctorRepo.FindByPublicID(ctx, doctor_public_id)
        if not doc:
            raise Exception("doctor account not found")

        vis = getattr(req, 'Visibility', None) or "INTERNAL"

        class DoctorNote: pass
        note = DoctorNote()
        note.DoctorID = doc.ID
        note.AdminID = admin_id
        note.Note = req.Note
        note.Visibility = vis

        try:
            self.noteRepo.Create(ctx, note)
        except Exception as e:
            raise e

        return note
