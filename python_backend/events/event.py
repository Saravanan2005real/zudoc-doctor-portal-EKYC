from datetime import datetime
from uuid import UUID

class BaseEvent:
    def __init__(self, event_type: str, doctor_id: UUID, timestamp: datetime):
        self.type = event_type
        self.doctor_id = doctor_id
        self.timestamp = timestamp

    def get_type(self) -> str:
        return self.type

    def get_doctor_id(self) -> UUID:
        return self.doctor_id

    def get_timestamp(self) -> datetime:
        return self.timestamp

class DoctorRegisteredEvent(BaseEvent):
    def __init__(self, doctor_id: UUID, timestamp: datetime, email: str, mobile: str):
        super().__init__("DoctorRegistered", doctor_id, timestamp)
        self.email = email
        self.mobile = mobile

class DocumentUploadedEvent(BaseEvent):
    def __init__(self, doctor_id: UUID, timestamp: datetime, document_id: UUID, document_type: str, file_url: str):
        super().__init__("DocumentUploaded", doctor_id, timestamp)
        self.document_id = document_id
        self.document_type = document_type
        self.file_url = file_url

class VerificationSubmittedEvent(BaseEvent):
    def __init__(self, doctor_id: UUID, timestamp: datetime, job_id: UUID):
        super().__init__("VerificationSubmitted", doctor_id, timestamp)
        self.job_id = job_id

class OCRCompletedEvent(BaseEvent):
    def __init__(self, doctor_id: UUID, timestamp: datetime, document_id: UUID, confidence: float):
        super().__init__("OCRCompleted", doctor_id, timestamp)
        self.document_id = document_id
        self.confidence = confidence

class DoctorVerifiedEvent(BaseEvent):
    def __init__(self, doctor_id: UUID, timestamp: datetime, approved_by: UUID):
        super().__init__("DoctorVerified", doctor_id, timestamp)
        self.approved_by = approved_by

class PrescriptionIssuedEvent(BaseEvent):
    def __init__(self, doctor_id: UUID, timestamp: datetime, prescription_id: UUID, patient_id: str):
        super().__init__("PrescriptionIssued", doctor_id, timestamp)
        self.prescription_id = prescription_id
        self.patient_id = patient_id
