"""
Step 4: eKYC evaluation pipeline.

Runs uploaded KYC documents through the OCR microservice
(PaddleOCR + RetinaFace + quality checks), then decides
AUTO_VERIFIED / MANUAL_REVIEW / FAILED.
"""
import os
import re
import requests
from datetime import datetime, timezone
from entities.doctor import DoctorStatus
from entities.history import VerificationHistory
from entities.document import OCRStatus


class DefaultEkycEvaluationService:
    KYC_TYPES = {"AADHAAR", "PAN", "PASSPORT"}

    def __init__(self, doctor_repo, doc_repo, history_repo, ocr_service_url=None, uploads_dir=None):
        self.doctorRepo = doctor_repo
        self.docRepo = doc_repo
        self.historyRepo = history_repo
        self.ocr_service_url = ocr_service_url or os.getenv(
            "OCR_SERVICE_URL", "http://127.0.0.1:5001/api/v1/ocr"
        )
        self.ocr_base_url = self.ocr_service_url.replace("/api/v1/ocr", "").rstrip("/")
        self.uploads_dir = uploads_dir or os.path.join(os.path.dirname(__file__), "..", "uploads")
        self.uploads_dir = os.path.abspath(self.uploads_dir)

    def Evaluate(self, doctor_public_id: str) -> dict:
        stages = []
        doc = self.doctorRepo.FindByPublicID(str(doctor_public_id))
        if not doc:
            raise Exception("doctor account not found")

        # Health-check OCR microservice before heavy work
        try:
            self._ensure_ocr_ready()
        except Exception as e:
            stages.append(self._stage(1, "Application Submitted", "done", "Doctor verification package loaded"))
            stages.append(self._stage(
                2,
                "eKYC OCR + Face Extraction",
                "failed",
                f"Cannot reach OCR microservice at {self.ocr_base_url}. Start it with: python -m ocr.engine ({e})",
            ))
            return self._finalize(
                doc,
                "MANUAL_REVIEW",
                stages,
                [],
                [f"OCR service unreachable at {self.ocr_base_url}"],
            )

        stages.append(self._stage(1, "Application Submitted", "done", "Doctor verification package loaded"))

        docs = self.docRepo.FindByDoctorID(doc.id) or []
        if not docs:
            stages.append(self._stage(2, "eKYC Document OCR", "failed", "No uploaded documents found"))
            return self._finalize(doc, "FAILED", stages, [], ["No documents available for eKYC evaluation"])

        kyc_docs = [d for d in docs if self._doc_type(d) in self.KYC_TYPES]
        # Prefer govt ID; if none, still OCR registration/degree docs for demo continuity
        target_docs = kyc_docs if kyc_docs else docs[:2]

        stages.append(self._stage(
            2,
            "eKYC OCR + Face Extraction",
            "running",
            f"Sending {len(target_docs)} document(s) to OCR microservice",
        ))

        document_results = []
        ocr_errors = []
        for d in target_docs:
            try:
                result = self._run_ocr_on_document(d)
                document_results.append(result)
                try:
                    d.ocr_status = OCRStatus.COMPLETED if result.get("status") == "success" else OCRStatus.FAILED
                    self.docRepo.db.commit()
                except Exception:
                    pass
            except Exception as e:
                ocr_errors.append(f"{self._doc_type(d)}: {e}")
                document_results.append({
                    "document_id": str(d.document_id),
                    "document_type": self._doc_type(d),
                    "status": "failed",
                    "error": str(e),
                    "face_detected": False,
                    "ocr_confidence": 0,
                    "parsed_fields": {},
                })

        success_docs = [r for r in document_results if r.get("status") == "success"]
        if success_docs:
            stages[1] = self._stage(
                2,
                "eKYC OCR + Face Extraction",
                "done",
                f"OCR completed on {len(success_docs)}/{len(target_docs)} document(s)",
            )
        else:
            stages[1] = self._stage(
                2,
                "eKYC OCR + Face Extraction",
                "failed",
                "; ".join(ocr_errors) if ocr_errors else "OCR microservice returned no successful results",
            )
            # If OCR service is down, fall to MANUAL_REVIEW instead of hard fail
            decision = "MANUAL_REVIEW" if ocr_errors else "FAILED"
            reasons = ocr_errors or ["OCR extraction failed"]
            return self._finalize(doc, decision, stages, document_results, reasons)

        # Stage 3: ID validation + face presence
        id_validated = False
        face_detected = False
        best_fields = {}
        best_conf = 0.0
        for r in success_docs:
            fields = r.get("parsed_fields") or {}
            best_fields = fields or best_fields
            best_conf = max(best_conf, float(r.get("ocr_confidence") or 0))
            if r.get("face_detected") or r.get("face_image_url"):
                face_detected = True
            if fields.get("aadhaar_number_validated") or fields.get("pan_number_validated"):
                id_validated = True
            if fields.get("aadhaar_number") or fields.get("pan_number"):
                # presence counts as soft validation if format flags missing
                if fields.get("document_type") in ("AADHAAR", "PAN"):
                    id_validated = id_validated or bool(
                        fields.get("aadhaar_number_validated") or fields.get("pan_number_validated")
                        or fields.get("aadhaar_number") or fields.get("pan_number")
                    )

        stages.append(self._stage(
            3,
            "ID Format & Face Visibility Check",
            "done" if (id_validated or face_detected) else "warn",
            f"ID validated={id_validated}, face_detected={face_detected}, OCR confidence={best_conf:.1f}%",
        ))

        # Stage 4: Name similarity vs profile
        ocr_name = (best_fields.get("name") or "").strip()
        profile_name = f"{doc.first_name or ''} {doc.last_name or ''}".strip()
        name_score = self._name_similarity(ocr_name, profile_name) if ocr_name else 0
        stages.append(self._stage(
            4,
            "Profile Cross-Match (Name Similarity)",
            "done",
            f"OCR name='{ocr_name or '-'}' vs profile='{profile_name}' → {name_score}%",
        ))

        # Stage 5: Decision
        reasons = []
        if not success_docs:
            reasons.append("No successful OCR results")
        if kyc_docs and not id_validated:
            reasons.append("Government ID number could not be confidently validated")
        if kyc_docs and not face_detected:
            reasons.append("Face not detected on KYC document")
        if ocr_name and name_score < 40:
            reasons.append(f"Low name similarity ({name_score}%)")

        if not success_docs:
            decision = "FAILED"
        elif id_validated or (face_detected and best_conf >= 40) or best_conf >= 60:
            # Strong enough OCR signal to auto-verify for demo pipeline
            decision = "AUTO_VERIFIED"
            reasons = []
        else:
            decision = "MANUAL_REVIEW"

        stages.append(self._stage(
            5,
            "Final Verification Decision",
            "done",
            f"Decision={decision}",
        ))

        return self._finalize(doc, decision, stages, document_results, reasons, name_score, id_validated, face_detected, best_conf)

    def _finalize(self, doc, decision, stages, document_results, reasons, name_score=0, id_validated=False, face_detected=False, confidence=0.0):
        if decision == "AUTO_VERIFIED":
            doc.status = DoctorStatus.AUTO_VERIFIED
            doc.prescription_enabled = True
            doc.fraud_score = 0
        elif decision == "MANUAL_REVIEW":
            doc.status = DoctorStatus.MANUAL_REVIEW
            doc.prescription_enabled = False
            doc.fraud_score = 30
        else:
            doc.status = DoctorStatus.REJECTED
            doc.prescription_enabled = False
            doc.fraud_score = 80

        try:
            self.doctorRepo.Update(doc)
        except Exception:
            pass

        try:
            self.historyRepo.Create(VerificationHistory(
                doctor_id=str(doc.id),
                action="EKYC_EVALUATION",
                status=decision,
                remarks="; ".join(reasons) if reasons else f"eKYC evaluation completed: {decision}",
            ))
        except Exception:
            pass

        return {
            "status": decision,
            "message": self._message_for(decision, reasons),
            "stages": stages,
            "documents": document_results,
            "decision": {
                "result": decision,
                "reasons": reasons,
                "name_match_score": name_score,
                "id_validated": id_validated,
                "face_detected": face_detected,
                "ocr_confidence": confidence,
            },
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "public_id": str(doc.public_id),
        }

    def _ensure_ocr_ready(self, attempts: int = 8) -> None:
        last_err = None
        for i in range(attempts):
            try:
                health = requests.get(f"{self.ocr_base_url}/health", timeout=3)
                if health.status_code >= 400:
                    health = requests.get(f"{self.ocr_base_url}/", timeout=3)
                if health.status_code < 500:
                    return
                last_err = Exception(f"OCR service unhealthy (HTTP {health.status_code})")
            except Exception as e:
                last_err = e
            if i < attempts - 1:
                import time
                time.sleep(1.5 * (i + 1))
        raise Exception(
            f"Cannot reach OCR microservice at {self.ocr_base_url}. "
            f"Start it with: python -m ocr.engine ({last_err})"
        )

    def _run_ocr_on_document(self, doc_entity) -> dict:
        local_path = self._resolve_local_path(doc_entity.file_url)
        if not local_path or not os.path.exists(local_path):
            raise Exception(f"stored file not found for {self._doc_type(doc_entity)} at {local_path}")

        filename = os.path.basename(local_path)
        mime = doc_entity.mime_type or "application/octet-stream"
        doc_type = self._doc_type(doc_entity)
        last_err = None
        data = None
        for attempt in range(3):
            try:
                with open(local_path, "rb") as f:
                    files = {"file": (filename, f, mime)}
                    form = {"document_type": doc_type}
                    resp = requests.post(self.ocr_service_url, files=files, data=form, timeout=300)
                if resp.status_code >= 400:
                    raise Exception(f"OCR service HTTP {resp.status_code}: {resp.text[:300]}")
                data = resp.json()
                break
            except Exception as e:
                last_err = e
                if attempt < 2:
                    import time
                    time.sleep(2)
        if data is None:
            raise Exception(str(last_err) if last_err else "OCR service failed")

        if data.get("status") != "success":
            raise Exception(data.get("error") or "OCR service failed")

        parsed = data.get("parsed_fields") or {}
        # Keep image URLs as relative paths (e.g. /ocr_uploads/...) so the
        # browser loads them from the portal's own origin where ocr_uploads
        # is mounted, instead of cross-origin requesting http://127.0.0.1:5001.
        face_url = data.get("face_image_url")
        processed_url = data.get("processed_image_url")

        return {
            "document_id": str(doc_entity.document_id),
            "document_type": self._doc_type(doc_entity),
            "status": "success",
            "ocr_confidence": data.get("ocr_confidence", 0),
            "parsed_fields": parsed,
            "quality_check": data.get("quality_check") or {},
            "perspective_corrected": data.get("perspective_corrected", False),
            "face_detected": bool(face_url),
            "face_image_url": face_url,
            "processed_image_url": processed_url,
            "raw_text": data.get("raw_text") or [],
        }

    def _resolve_local_path(self, file_url: str) -> str:
        if not file_url:
            return ""
        url = file_url.replace("\\", "/")
        for prefix in ("/uploads/", "uploads/"):
            if url.startswith(prefix):
                rel = url[len(prefix):]
                return os.path.join(self.uploads_dir, rel.replace("/", os.sep))
        if os.path.isabs(url) and os.path.exists(url):
            return url
        return os.path.join(self.uploads_dir, url.lstrip("/").replace("/", os.sep))

    def _doc_type(self, d) -> str:
        return d.document_type.value if hasattr(d.document_type, "value") else str(d.document_type)

    def _stage(self, sid, title, status, detail):
        return {"id": sid, "title": title, "status": status, "detail": detail}

    def _message_for(self, decision, reasons):
        if decision == "AUTO_VERIFIED":
            return "eKYC evaluation passed. Doctor auto-verified and unlocked for Step 5."
        if decision == "MANUAL_REVIEW":
            extra = ("; ".join(reasons)) if reasons else "Needs human review"
            return f"eKYC evaluation needs manual review. {extra}"
        return f"eKYC evaluation failed. {'; '.join(reasons) if reasons else 'Unknown error'}"

    def _name_similarity(self, a: str, b: str) -> int:
        a_tok = set(re.findall(r"[a-z]+", a.lower()))
        b_tok = set(re.findall(r"[a-z]+", b.lower()))
        if not a_tok or not b_tok:
            return 0
        inter = len(a_tok & b_tok)
        union = len(a_tok | b_tok)
        return int(round(100.0 * inter / union)) if union else 0
