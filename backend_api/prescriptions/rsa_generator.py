import json
import base64
import uuid
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization

class RSADigitalPrescription:
    def __init__(self, prescription_id, doctor_id, patient_id, diagnosis, medicines, digital_signature, public_key_pem, qr_payload, issued_at):
        self.prescription_id = prescription_id
        self.doctor_id = doctor_id
        self.patient_id = patient_id
        self.diagnosis = diagnosis
        self.medicines = medicines
        self.digital_signature = digital_signature
        self.public_key_pem = public_key_pem
        self.qr_payload = qr_payload
        self.issued_at = issued_at

class RSAPrescriptionGenerator:
    def __init__(self):
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self.public_key = self.private_key.public_key()

    def issue_prescription(self, doctor, patient_id: str, diagnosis: str, medicines: list) -> RSADigitalPrescription:
        if doctor.status != "VERIFIED" or not doctor.prescription_enabled:
            raise ValueError(f"doctor '{doctor.public_id}' is not authorized to issue digital prescriptions")

        prescription_id = uuid.uuid4()
        issued_at = datetime.now()
        meds_json = json.dumps(medicines, separators=(',', ':'))

        signature_input = f"{prescription_id}|{doctor.public_id}|{patient_id}|{diagnosis}|{meds_json}|{issued_at.isoformat()}Z"

        signature_bytes = self.private_key.sign(
            signature_input.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        digital_signature = base64.b64encode(signature_bytes).decode('utf-8')

        pub_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        qr_data = {
            "pid": str(prescription_id),
            "doc": str(doctor.public_id),
            "name": f"{doctor.first_name} {doctor.last_name}",
            "pat": patient_id,
            "sig": digital_signature[:24],
            "ts": int(issued_at.timestamp()),
            "url": f"https://practo-doctor.portal/prescriptions/{prescription_id}/verify"
        }

        qr_json = json.dumps(qr_data, separators=(',', ':'))
        qr_payload = base64.b64encode(qr_json.encode('utf-8')).decode('utf-8')

        return RSADigitalPrescription(
            prescription_id=prescription_id,
            doctor_id=doctor.public_id,
            patient_id=patient_id,
            diagnosis=diagnosis,
            medicines=medicines,
            digital_signature=digital_signature,
            public_key_pem=pub_pem,
            qr_payload=qr_payload,
            issued_at=issued_at
        )

def verify_rsa_signature(p: RSADigitalPrescription) -> bool:
    if not p.public_key_pem or not p.digital_signature:
        raise ValueError("missing public key or digital signature")

    try:
        public_key = serialization.load_pem_public_key(
            p.public_key_pem.encode('utf-8')
        )
    except Exception as e:
        raise ValueError(f"failed to parse public key: {e}")

    meds_json = json.dumps(p.medicines, separators=(',', ':'))
    signature_input = f"{p.prescription_id}|{p.doctor_id}|{p.patient_id}|{p.diagnosis}|{meds_json}|{p.issued_at.isoformat()}Z"

    try:
        sig_bytes = base64.b64decode(p.digital_signature)
    except Exception as e:
        raise ValueError(f"failed to decode signature base64: {e}")

    try:
        public_key.verify(
            sig_bytes,
            signature_input.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False
