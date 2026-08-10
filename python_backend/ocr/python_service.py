import time
import requests
from ocr.provider import OCRProvider, OCRResult, ExtractedFields

class PythonOCRProvider(OCRProvider):
    def __init__(self, service_url: str = ""):
        self.service_url = service_url or "http://127.0.0.1:5001/api/v1/ocr"

    def extract(self, context, doc, file_reader) -> OCRResult:
        start = time.time()

        files = {'file': ('document.png', file_reader)}
        response = requests.post(self.service_url, files=files, timeout=30)
        
        if response.status_code >= 400:
            raise ValueError(f"failed to call Python OCR service: status code {response.status_code}")

        py_resp = response.json()

        if py_resp.get("status") != "success":
            raise ValueError(f"python OCR service returned error: {py_resp.get('error')}")

        fields = ExtractedFields()
        parsed_fields = py_resp.get("parsed_fields", {})
        
        if parsed_fields.get("name"):
            fields.doctor_name = parsed_fields["name"]
        if parsed_fields.get("dob"):
            fields.dob = parsed_fields["dob"]
        if parsed_fields.get("aadhaar_number"):
            fields.govt_id_number = parsed_fields["aadhaar_number"]
        elif parsed_fields.get("pan_number"):
            fields.govt_id_number = parsed_fields["pan_number"]

        processing_time = int((time.time() - start) * 1000)

        return OCRResult(
            raw_json=response.text,
            parsed_fields=fields,
            confidence=py_resp.get("ocr_confidence", 0.0),
            processing_time_ms=processing_time
        )

    def get_provider_name(self) -> str:
        return "PYTHON_PADDLE_OCR"
