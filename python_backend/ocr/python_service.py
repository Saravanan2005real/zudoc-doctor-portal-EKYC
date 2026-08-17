import time
import os
import uuid
import cv2
import numpy as np
from ocr.provider import OCRProvider, OCRResult, ExtractedFields
from ocr.engine import check_image_quality, detect_and_warp_document, extract_and_align_face, best_ocr_pass

class PythonOCRProvider(OCRProvider):
    def __init__(self, service_url: str = ""):
        self.upload_folder = "./uploads/ocr"
        os.makedirs(self.upload_folder, exist_ok=True)

    def extract(self, context, doc, file_reader) -> OCRResult:
        start = time.time()

        file_bytes = file_reader.read()
        np_arr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Invalid image format")

        filename_id = str(uuid.uuid4())

        warped_img, warped_ok = detect_and_warp_document(img)
        face_img = extract_and_align_face(warped_img)

        if face_img is not None:
            face_path = os.path.join(self.upload_folder, f"face_{filename_id}.jpg")
            cv2.imwrite(face_path, face_img)

        processed_img, extracted_lines, confidence_scores, avg_confidence, parsed_fields_dict, ocr_pass = best_ocr_pass(
            warped_img, self.upload_folder, filename_id
        )

        fields = ExtractedFields()
        if parsed_fields_dict.get("name"):
            fields.doctor_name = parsed_fields_dict["name"]
        if parsed_fields_dict.get("dob"):
            fields.dob = parsed_fields_dict["dob"]
        if parsed_fields_dict.get("aadhaar_number"):
            fields.govt_id_number = parsed_fields_dict["aadhaar_number"]
        elif parsed_fields_dict.get("pan_number"):
            fields.govt_id_number = parsed_fields_dict["pan_number"]

        processing_time = int((time.time() - start) * 1000)

        return OCRResult(
            raw_json="{}",
            parsed_fields=fields,
            confidence=avg_confidence * 100 if avg_confidence else 0.0,
            processing_time_ms=processing_time
        )

    def get_provider_name(self) -> str:
        return "PYTHON_PADDLE_OCR_NATIVE"
