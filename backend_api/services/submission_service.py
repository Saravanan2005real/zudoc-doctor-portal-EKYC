from datetime import datetime, timezone
from entities.doctor import DoctorStatus
from entities.history import VerificationHistory
from entities.job import VerificationJob, JobType, JobStatus


class SubmissionService:
    def SubmitVerification(self, ctx, doctor_public_id):
        pass


class DefaultSubmissionService(SubmissionService):
    def __init__(self, doctor_repo, license_repo, qual_repo, clinic_repo, doc_repo, history_repo, job_repo):
        self.doctorRepo = doctor_repo
        self.licenseRepo = license_repo
        self.qualRepo = qual_repo
        self.clinicRepo = clinic_repo
        self.docRepo = doc_repo
        self.historyRepo = history_repo
        self.jobRepo = job_repo

    def SubmitVerification(self, ctx, doctor_public_id):
        doc = self.doctorRepo.FindByPublicID(str(doctor_public_id))
        if not doc:
            raise Exception("doctor account not found")

        missing_checklist = []

        if not doc.mobile_verified:
            missing_checklist.append("Mobile number verification pending")

        licenses = self.licenseRepo.FindByDoctorID(doc.id) or []
        if not licenses:
            missing_checklist.append("At least one medical registration license is required")

        quals = self.qualRepo.FindByDoctorID(doc.id) or []
        if not quals:
            missing_checklist.append("At least one medical qualification degree is required")

        clinics = self.clinicRepo.FindByDoctorID(doc.id) or []
        if not clinics:
            missing_checklist.append("At least one clinic listing is required")

        uploaded_docs = self.docRepo.FindByDoctorID(doc.id) or []
        has_registration_cert = False
        has_degree_cert = False
        has_govt_id = False

        for d in uploaded_docs:
            dtype = d.document_type.value if hasattr(d.document_type, "value") else str(d.document_type)
            if dtype == "REGISTRATION_CERTIFICATE":
                has_registration_cert = True
            elif dtype in ("MBBS_CERTIFICATE", "MD_CERTIFICATE", "MEDICAL_DEGREE_CERTIFICATE"):
                has_degree_cert = True
            elif dtype in ("AADHAAR", "PAN", "PASSPORT"):
                has_govt_id = True

        if not has_registration_cert:
            missing_checklist.append("Medical Registration Certificate document is missing")
        if not has_degree_cert:
            missing_checklist.append("Medical Degree Certificate document is missing")
        if not has_govt_id:
            missing_checklist.append("Government Identity proof (Aadhaar, PAN, or Passport) is missing")

        if missing_checklist:
            missing_str = "\n- ".join(missing_checklist)
            raise Exception(f"verification submission rejected. Incomplete profile checklist:\n- {missing_str}")

        doc.status = DoctorStatus.PENDING
        try:
            self.doctorRepo.Update(doc)
        except Exception as e:
            raise Exception(f"failed to update doctor status: {e}")

        try:
            self.historyRepo.Create(
                VerificationHistory(
                    doctor_id=str(doc.id),
                    action="SUBMISSION_COMPLETED",
                    status="PENDING",
                    remarks="Doctor submitted profile and all mandatory documents for verification.",
                )
            )
        except Exception:
            pass

        if self.jobRepo:
            try:
                self.jobRepo.Create(
                    VerificationJob(
                        doctor_id=str(doc.id),
                        job_type=JobType.FULL_PIPELINE,
                        status=JobStatus.QUEUED,
                        priority=1,
                        max_retries=3,
                    )
                )
            except Exception:
                pass

        class SubmitVerificationResponse:
            pass

        resp = SubmitVerificationResponse()
        resp.message = (
            "Doctor verification application submitted successfully. "
            "Your profile has been queued for background OCR and council verification."
        )
        resp.public_id = str(doc.public_id)
        resp.status = doc.status.value if hasattr(doc.status, "value") else str(doc.status)
        resp.submitted_at = datetime.now(timezone.utc)
        return resp
