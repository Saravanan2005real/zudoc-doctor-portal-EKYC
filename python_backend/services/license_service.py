from datetime import datetime
from entities.license import DoctorLicense, VerificationStatus


class LicenseService:
    def AddLicense(self, ctx, doctor_id, req):
        pass

    def GetLicenses(self, ctx, doctor_id):
        pass

    def DeleteLicense(self, ctx, license_id, doctor_id):
        pass


class DefaultLicenseService(LicenseService):
    def __init__(self, doctor_repo, license_repo):
        self.doctorRepo = doctor_repo
        self.licenseRepo = license_repo

    def _to_response(self, license):
        class LicenseResponse:
            pass

        resp = LicenseResponse()
        resp.license_id = str(license.license_id)
        resp.registration_number = license.registration_number
        resp.registration_council = license.registration_council
        resp.registration_year = license.registration_year
        resp.license_status = license.license_status or "ACTIVE"
        resp.verification_status = (
            license.verification_status.value
            if hasattr(license.verification_status, "value")
            else str(license.verification_status)
        )
        resp.created_at = license.created_at or datetime.utcnow()
        return resp

    def AddLicense(self, ctx, doctor_id, req):
        doc = self.doctorRepo.FindByPublicID(str(doctor_id))
        if not doc:
            raise Exception("doctor not found")

        issue_date = None
        expiry_date = None
        if getattr(req, "issue_date", None):
            try:
                issue_date = datetime.strptime(req.issue_date, "%Y-%m-%d")
            except ValueError:
                pass
        if getattr(req, "expiry_date", None):
            try:
                expiry_date = datetime.strptime(req.expiry_date, "%Y-%m-%d")
            except ValueError:
                pass

        license_entity = DoctorLicense(
            doctor_id=str(doc.id),
            registration_number=req.registration_number,
            registration_council=req.registration_council,
            registration_year=req.registration_year,
            issue_date=issue_date,
            expiry_date=expiry_date,
            license_status="ACTIVE",
            verification_status=VerificationStatus.UNVERIFIED,
        )
        self.licenseRepo.Create(license_entity)
        return self._to_response(license_entity)

    def GetLicenses(self, ctx, doctor_id):
        doc = self.doctorRepo.FindByPublicID(str(doctor_id))
        if not doc:
            raise Exception("doctor not found")
        licenses = self.licenseRepo.FindByDoctorID(doc.id)
        return [self._to_response(l) for l in licenses]

    def DeleteLicense(self, ctx, license_id, doctor_id):
        doc = self.doctorRepo.FindByPublicID(str(doctor_id))
        if not doc:
            raise Exception("doctor not found")
        return self.licenseRepo.Delete(str(license_id), doc.id)
