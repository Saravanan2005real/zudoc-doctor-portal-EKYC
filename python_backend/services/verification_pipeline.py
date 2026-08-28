import uuid
import json
import requests
from datetime import datetime

class VerificationPipelineService:
    def ProcessVerificationJob(self, ctx, job_id): pass

class DefaultVerificationPipelineService(VerificationPipelineService):
    def __init__(self, job_repo, doctor_repo, doc_repo, license_repo, qual_repo, history_repo, ocr_repo, ocr_provider, comparator, council_provider, fraud_detector, decision_engine):
        self.jobRepo = job_repo
        self.doctorRepo = doctor_repo
        self.docRepo = doc_repo
        self.licenseRepo = license_repo
        self.qualRepo = qual_repo
        self.historyRepo = history_repo
        self.ocrRepo = ocr_repo
        self.ocrProvider = ocr_provider
        self.comparator = comparator
        self.councilProvider = council_provider
        self.fraudDetector = fraud_detector
        self.decisionEngine = decision_engine

    def ProcessVerificationJob(self, ctx, job_id):
        try:
            self.jobRepo.MarkRunning(ctx, job_id)
        except Exception as e:
            raise e

        pipeline_err = None
        
        try:
            current_job = self.jobRepo.FindByID(ctx, job_id)
            if not current_job:
                pipeline_err = Exception("verification job record not found")
                raise pipeline_err

            doc = None
            try:
                doc = self.doctorRepo.FindByPublicID(ctx, current_job.DoctorID)
            except Exception:
                pass
                
            if not doc:
                try:
                    doc = self.doctorRepo.FindByEmail(ctx, "")
                except Exception:
                    pass
                if not doc:
                    pipeline_err = Exception(f"doctor record not found for job: {current_job.DoctorID}")
                    raise pipeline_err

            try: licenses = self.licenseRepo.FindByDoctorID(ctx, doc.ID)
            except Exception: licenses = []
            try: quals = self.qualRepo.FindByDoctorID(ctx, doc.ID)
            except Exception: quals = []
            try: docs = self.docRepo.FindByDoctorID(ctx, doc.ID)
            except Exception: docs = []

            if not docs:
                pipeline_err = Exception("no uploaded documents found for verification")
                raise pipeline_err

            class OCRFields:
                DoctorName = ""
                RegistrationNumber = ""
                RegistrationCouncil = ""
                RegistrationYear = ""
                Degree = ""
                University = ""
                
            combined_ocr_fields = OCRFields()
            total_confidence = 0.0
            doc_count = 0

            for d in docs:
                try:
                    resp = requests.get(d.FileURL, stream=True)
                    resp.raise_for_status()
                except Exception:
                    continue
                    
                try:
                    ocr_res = self.ocrProvider.Extract(ctx, d, resp.raw)
                    doc_count += 1
                    total_confidence += ocr_res.Confidence

                    if getattr(ocr_res.ParsedFields, 'DoctorName', ""):
                        combined_ocr_fields.DoctorName = ocr_res.ParsedFields.DoctorName
                    if getattr(ocr_res.ParsedFields, 'RegistrationNumber', ""):
                        combined_ocr_fields.RegistrationNumber = ocr_res.ParsedFields.RegistrationNumber
                        combined_ocr_fields.RegistrationCouncil = ocr_res.ParsedFields.RegistrationCouncil
                        combined_ocr_fields.RegistrationYear = ocr_res.ParsedFields.RegistrationYear
                    if getattr(ocr_res.ParsedFields, 'Degree', ""):
                        combined_ocr_fields.Degree = ocr_res.ParsedFields.Degree
                        combined_ocr_fields.University = ocr_res.ParsedFields.University

                    parsed_json = json.dumps(ocr_res.ParsedFields.__dict__ if hasattr(ocr_res.ParsedFields, '__dict__') else ocr_res.ParsedFields)
                    
                    class DocumentOCRResult: pass
                    ocr_record = DocumentOCRResult()
                    ocr_record.DocumentID = d.DocumentID
                    ocr_record.Provider = self.ocrProvider.GetProviderName()
                    ocr_record.RawJSON = getattr(ocr_res, 'RawJSON', "")
                    ocr_record.ParsedJSON = parsed_json
                    ocr_record.Confidence = ocr_res.Confidence
                    ocr_record.ProcessingTimeMS = ocr_res.ProcessingTimeMS
                    
                    try: self.ocrRepo.Create(ctx, ocr_record)
                    except Exception: pass
                    
                except Exception:
                    pass
                finally:
                    resp.close()

            avg_confidence = 95.0
            if doc_count > 0:
                avg_confidence = total_confidence / float(doc_count)

            comp_result = self.comparator.CompareDoctorWithOCR(doc, licenses, quals, combined_ocr_fields)

            reg_no = ""
            council_name = ""
            if licenses:
                reg_no = licenses[0].RegistrationNumber
                council_name = licenses[0].RegistrationCouncil
                
            try:
                council_result, _ = self.councilProvider.Verify(ctx, reg_no, council_name)
            except Exception:
                council_result = None

            fraud_result = self.fraudDetector.Analyze(
                ctx,
                comp_result,
                council_result,
                avg_confidence,
                False,
                False
            )

            doc.FraudScore = fraud_result.FraudScore

            dec_result = self.decisionEngine.Evaluate(comp_result, council_result, fraud_result, avg_confidence)

            doc.Status = dec_result.FinalStatus
            try:
                self.doctorRepo.Update(ctx, doc)
            except Exception as e:
                pipeline_err = Exception(f"failed to update doctor status: {e}")
                raise pipeline_err

            remarks = f"{dec_result.Reason} (Overall Match: {comp_result.OverallMatchScore:.1f}%, Fraud Score: {fraud_result.FraudScore}/100)"
            
            class VerificationHistory: pass
            history = VerificationHistory()
            history.DoctorID = doc.ID
            history.Action = f"AUTOMATED_VERIFICATION_{dec_result.FinalStatus}"
            history.Status = str(dec_result.FinalStatus)
            history.Remarks = remarks
            history.PerformedAt = datetime.now()
            
            try: self.historyRepo.Create(ctx, history)
            except Exception: pass

            return None

        except Exception as e:
            pipeline_err = e
            raise e
        finally:
            if pipeline_err:
                try: self.jobRepo.MarkFailed(ctx, job_id, str(pipeline_err))
                except Exception: pass
            else:
                try: self.jobRepo.MarkCompleted(ctx, job_id)
                except Exception: pass
