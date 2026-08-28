import hmac
import hashlib
import base64
import json
from datetime import datetime
import uuid

class DigitalPrescription:
    def __init__(self, prescription_id, doctor_id, patient_id, diagnosis, medicines, digital_signature, qr_payload, issued_at):
        self.prescription_id = prescription_id
        self.doctor_id = doctor_id
        self.patient_id = patient_id
        self.diagnosis = diagnosis
        self.medicines = medicines
        self.digital_signature = digital_signature
        self.qr_payload = qr_payload
        self.issued_at = issued_at

class PrescriptionGenerator:
    def __init__(self, secret_key: str = ""):
        if not secret_key:
            secret_key = "digital-prescription-signing-rsa-secret-key"
        self.signing_secret = secret_key.encode('utf-8')

    def issue_prescription(self, doctor, patient_id: str, diagnosis: str, medicines: list) -> DigitalPrescription:
        if doctor.status != "VERIFIED" or not doctor.prescription_enabled:
            raise ValueError(f"doctor '{doctor.public_id}' is not authorized to issue digital prescriptions")

        prescription_id = uuid.uuid4()
        issued_at = datetime.now()

        meds_json = json.dumps(medicines, separators=(',', ':'))

        signature_input = f"{prescription_id}|{doctor.public_id}|{patient_id}|{diagnosis}|{meds_json}|{issued_at.isoformat()}Z"

        h = hmac.new(self.signing_secret, signature_input.encode('utf-8'), hashlib.sha256)
        digital_signature = h.hexdigest()

        qr_data = {
            "pid": str(prescription_id),
            "doc": str(doctor.public_id),
            "name": f"{doctor.first_name} {doctor.last_name}",
            "pat": patient_id,
            "sig": digital_signature[:16],
            "ts": int(issued_at.timestamp()),
            "url": f"https://practo-doctor.portal/prescriptions/{prescription_id}/verify"
        }

        qr_json = json.dumps(qr_data, separators=(',', ':'))
        qr_payload = base64.b64encode(qr_json.encode('utf-8')).decode('utf-8')

        return DigitalPrescription(
            prescription_id=prescription_id,
            doctor_id=doctor.public_id,
            patient_id=patient_id,
            diagnosis=diagnosis,
            medicines=medicines,
            digital_signature=digital_signature,
            qr_payload=qr_payload,
            issued_at=issued_at
        )

    def verify_signature(self, p: DigitalPrescription) -> bool:
        meds_json = json.dumps(p.medicines, separators=(',', ':'))
        signature_input = f"{p.prescription_id}|{p.doctor_id}|{p.patient_id}|{p.diagnosis}|{meds_json}|{p.issued_at.isoformat()}Z"

        h = hmac.new(self.signing_secret, signature_input.encode('utf-8'), hashlib.sha256)
        expected_sig = h.hexdigest()

        return hmac.compare_digest(p.digital_signature, expected_sig)
