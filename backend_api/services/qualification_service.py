from datetime import datetime
from entities.qualification import DoctorQualification


class QualificationService:
    def AddQualification(self, ctx, doctor_id, req):
        pass

    def GetQualifications(self, ctx, doctor_id):
        pass

    def DeleteQualification(self, ctx, qualification_id, doctor_id):
        pass


class DefaultQualificationService(QualificationService):
    def __init__(self, doctor_repo, qual_repo):
        self.doctorRepo = doctor_repo
        self.qualRepo = qual_repo

    def _to_response(self, qual):
        class QualificationResponse:
            pass

        resp = QualificationResponse()
        resp.qualification_id = str(qual.qualification_id)
        resp.degree = qual.degree
        resp.specialization = qual.specialization or ""
        resp.college = qual.college
        resp.university = qual.university
        resp.year_completed = qual.year_completed
        resp.created_at = qual.created_at or datetime.utcnow()
        return resp

    def AddQualification(self, ctx, doctor_id, req):
        doc = self.doctorRepo.FindByPublicID(str(doctor_id))
        if not doc:
            raise Exception("doctor not found")

        qual = DoctorQualification(
            doctor_id=str(doc.id),
            degree=req.degree,
            specialization=getattr(req, "specialization", None) or "",
            college=req.college,
            university=req.university,
            year_completed=req.year_completed,
        )
        self.qualRepo.Create(qual)
        return self._to_response(qual)

    def GetQualifications(self, ctx, doctor_id):
        doc = self.doctorRepo.FindByPublicID(str(doctor_id))
        if not doc:
            raise Exception("doctor not found")
        quals = self.qualRepo.FindByDoctorID(doc.id)
        return [self._to_response(q) for q in quals]

    def DeleteQualification(self, ctx, qualification_id, doctor_id):
        doc = self.doctorRepo.FindByPublicID(str(doctor_id))
        if not doc:
            raise Exception("doctor not found")
        return self.qualRepo.Delete(str(qualification_id), doc.id)
