import uuid
from datetime import datetime

class ProfileService:
    def UpdateProfile(self, ctx, doctor_id, req): pass
    def GetProfile(self, ctx, doctor_id): pass

class DefaultProfileService(ProfileService):
    def __init__(self, doctor_repo):
        self.doctorRepo = doctor_repo

    def UpdateProfile(self, ctx, doctor_id, req):
        doc = self.doctorRepo.FindByPublicID(ctx, doctor_id)
        if not doc:
            raise Exception("doctor profile not found")

        if getattr(req, 'Gender', None):
            doc.Gender = req.Gender
        if getattr(req, 'ProfilePhoto', None):
            doc.ProfilePhoto = req.ProfilePhoto
        if getattr(req, 'Languages', None):
            doc.Languages = req.Languages
        if getattr(req, 'Biography', None):
            doc.Biography = req.Biography
        if getattr(req, 'DOB', None):
            try:
                doc.DOB = datetime.strptime(req.DOB, "%Y-%m-%d")
            except ValueError:
                pass

        try:
            self.doctorRepo.Update(ctx, doc)
        except Exception as e:
            raise e

        class DoctorProfileDTO: pass
        resp = DoctorProfileDTO()
        resp.PublicID = doc.PublicID
        resp.FirstName = doc.FirstName
        resp.LastName = doc.LastName
        resp.Email = doc.Email
        resp.Mobile = doc.Mobile
        resp.Status = str(doc.Status)
        resp.MobileVerified = doc.MobileVerified
        resp.EmailVerified = doc.EmailVerified
        return resp

    def GetProfile(self, ctx, doctor_id):
        doc = self.doctorRepo.FindByPublicID(ctx, doctor_id)
        if not doc:
            raise Exception("doctor profile not found")

        class DoctorProfileDTO: pass
        resp = DoctorProfileDTO()
        resp.PublicID = doc.PublicID
        resp.FirstName = doc.FirstName
        resp.LastName = doc.LastName
        resp.Email = doc.Email
        resp.Mobile = doc.Mobile
        resp.Status = str(doc.Status)
        resp.MobileVerified = doc.MobileVerified
        resp.EmailVerified = doc.EmailVerified
        return resp
