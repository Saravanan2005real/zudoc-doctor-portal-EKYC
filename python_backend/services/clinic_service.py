from datetime import datetime
from decimal import Decimal
from entities.clinic import DoctorClinic, ConsultationMode


class ClinicService:
    def AddClinic(self, ctx, doctor_id, req):
        pass

    def GetClinics(self, ctx, doctor_id):
        pass

    def DeleteClinic(self, ctx, clinic_id, doctor_id):
        pass


class DefaultClinicService(ClinicService):
    def __init__(self, doctor_repo, clinic_repo):
        self.doctorRepo = doctor_repo
        self.clinicRepo = clinic_repo

    def _to_response(self, clinic):
        class ClinicResponse:
            pass

        resp = ClinicResponse()
        resp.clinic_id = str(clinic.clinic_id)
        resp.clinic_name = clinic.clinic_name
        resp.address = clinic.address
        resp.city = clinic.city
        resp.state = clinic.state
        resp.pincode = clinic.pincode
        resp.consultation_mode = (
            clinic.consultation_mode.value
            if hasattr(clinic.consultation_mode, "value")
            else str(clinic.consultation_mode)
        )
        resp.consultation_fee = float(clinic.consultation_fee or 0)
        resp.created_at = clinic.created_at or datetime.utcnow()
        return resp

    def AddClinic(self, ctx, doctor_id, req):
        doc = self.doctorRepo.FindByPublicID(str(doctor_id))
        if not doc:
            raise Exception("doctor not found")

        mode_raw = getattr(req, "consultation_mode", None) or "IN_PERSON"
        if mode_raw == "OFFLINE":
            mode_raw = "IN_PERSON"
        try:
            mode = ConsultationMode(mode_raw)
        except Exception:
            mode = ConsultationMode.IN_PERSON

        fee = getattr(req, "consultation_fee", None)
        if fee is None:
            fee = 0

        clinic = DoctorClinic(
            doctor_id=str(doc.id),
            clinic_name=req.clinic_name,
            address=req.address,
            city=req.city,
            state=req.state,
            pincode=req.pincode,
            latitude=getattr(req, "latitude", None),
            longitude=getattr(req, "longitude", None),
            consultation_mode=mode,
            consultation_fee=Decimal(str(fee)),
        )
        self.clinicRepo.Create(clinic)
        return self._to_response(clinic)

    def GetClinics(self, ctx, doctor_id):
        doc = self.doctorRepo.FindByPublicID(str(doctor_id))
        if not doc:
            raise Exception("doctor not found")
        clinics = self.clinicRepo.FindByDoctorID(doc.id)
        return [self._to_response(c) for c in clinics]

    def DeleteClinic(self, ctx, clinic_id, doctor_id):
        doc = self.doctorRepo.FindByPublicID(str(doctor_id))
        if not doc:
            raise Exception("doctor not found")
        return self.clinicRepo.Delete(str(clinic_id), doc.id)
