import time
import json
from ocr.provider import OCRProvider, OCRResult, ExtractedFields

class MockOCRProvider(OCRProvider):
    def extract(self, context, doc, file_reader) -> OCRResult:
        start = time.time()
        confidence = 96.5

        if doc.document_type == "RegistrationCertificate":
            fields = ExtractedFields(
                doctor_name="Dr. Rahul Kumar",
                registration_number="123456",
                registration_council="Tamil Nadu Medical Council",
                registration_year=2021,
                degree="MBBS"
            )
        elif doc.document_type in ("MBBSCertificate", "MDCertificate"):
            fields = ExtractedFields(
                doctor_name="Rahul Kumar",
                degree="MBBS",
                university="The Tamil Nadu Dr. M.G.R. Medical University",
                college="Stanley Medical College",
                year_completed=2020
            )
        elif doc.document_type in ("Aadhaar", "PAN", "Passport"):
            fields = ExtractedFields(
                doctor_name="Rahul Kumar",
                dob="1995-05-15",
                govt_id_number="9999-8888-7777"
            )
        else:
            fields = ExtractedFields(doctor_name="Rahul Kumar")

        parsed_json = json.dumps(fields.__dict__)
        raw_json = f'{{"engine":"mock_ocr_v1","status":"success","extracted":{parsed_json}}}'
        processing_time = int((time.time() - start) * 1000)

        return OCRResult(
            raw_json=raw_json,
            parsed_fields=fields,
            confidence=confidence,
            processing_time_ms=processing_time
        )

    def get_provider_name(self) -> str:
        return "MOCK_OCR"
