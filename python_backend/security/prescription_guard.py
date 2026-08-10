import json
from uuid import UUID

class PrescriptionAuthGuard:
    def __init__(self, doctor_repo):
        self.doctor_repo = doctor_repo

    def require_verified_doctor_for_prescription(self, request, next_handler):
        doc_id_str = request.headers.get("X-Doctor-Public-ID")
        if not doc_id_str:
            return {"error": "Unauthorized: Missing X-Doctor-Public-ID header"}, 401
        
        try:
            doc_uuid = UUID(doc_id_str)
        except ValueError:
            return {"error": "Unauthorized: Invalid X-Doctor-Public-ID header format"}, 401
            
        doc = self.doctor_repo.find_by_public_id(request.context, doc_uuid)
        if not doc:
            return {"error": "Unauthorized: Doctor account not found"}, 401
            
        if doc.status != "VERIFIED":
            return {"error": "Forbidden: Doctor verification incomplete. Only VERIFIED doctors can generate digital prescriptions or conduct teleconsultations."}, 403
            
        if not doc.prescription_enabled:
            return {"error": "Forbidden: Digital prescription enablement is disabled on this profile. Please contact medical compliance."}, 403
            
        request.context["verified_doctor"] = doc
        return next_handler(request)
