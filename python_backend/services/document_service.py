import io
import uuid
from datetime import datetime, timezone
from entities.document import DoctorDocument, DocumentType, OCRStatus


class DocumentService:
    def UploadDocument(self, ctx, doctor_public_id, doc_type, file, filename, size):
        pass

    def GetDoctorDocuments(self, ctx, doctor_public_id):
        pass

    def DeleteDocument(self, ctx, document_id, doctor_public_id):
        pass


class DefaultDocumentService(DocumentService):
    def __init__(self, doctor_repo, doc_repo, storage_provider, validator, scanner):
        self.doctorRepo = doctor_repo
        self.docRepo = doc_repo
        self.storageProvider = storage_provider
        self.validator = validator
        self.scanner = scanner

    def _to_response(self, doc_entity, doctor_public_id):
        class DocumentUploadResponse:
            pass

        resp = DocumentUploadResponse()
        resp.document_id = str(doc_entity.document_id)
        resp.doctor_id = str(doctor_public_id)
        resp.document_type = (
            doc_entity.document_type.value
            if hasattr(doc_entity.document_type, "value")
            else str(doc_entity.document_type)
        )
        resp.file_url = doc_entity.file_url
        resp.original_filename = doc_entity.original_filename
        resp.mime_type = doc_entity.mime_type
        resp.file_size = int(doc_entity.file_size or 0)
        resp.file_hash = doc_entity.file_hash or ""
        resp.version = int(doc_entity.version or 1)
        resp.is_latest = bool(doc_entity.is_latest)
        resp.ocr_status = (
            doc_entity.ocr_status.value
            if hasattr(doc_entity.ocr_status, "value")
            else str(doc_entity.ocr_status)
        )
        resp.uploaded_at = doc_entity.uploaded_at or datetime.now(timezone.utc)
        return resp

    def UploadDocument(self, ctx, doctor_public_id, doc_type, file, filename, size):
        try:
            doc = self.doctorRepo.FindByPublicID(str(doctor_public_id))
            if not doc:
                raise Exception("doctor account not found")

            # Ensure stream is seekable bytes for validator/storage
            if hasattr(file, "seek"):
                try:
                    file.seek(0)
                except Exception:
                    pass
            raw = file.read() if hasattr(file, "read") else file
            stream = io.BytesIO(raw if isinstance(raw, (bytes, bytearray)) else bytes(raw))
            declared_size = size if size and size > 0 else len(stream.getvalue())

            try:
                val_res = self.validator.validate(stream, filename, declared_size)
            except Exception as e:
                raise Exception(f"file validation failed: {e}")

            stream.seek(0)
            try:
                clean, scan_msg = self.scanner.scan(ctx, stream, filename)
                if not clean:
                    raise Exception(f"virus scan check failed ({scan_msg})")
            except Exception as e:
                if "virus scan" in str(e):
                    raise
                raise Exception(f"virus scan check failed: {e}")

            stream.seek(0)
            existing_hash_doc = self.docRepo.FindByHash(doc.id, val_res.file_hash)
            if existing_hash_doc:
                existing_type = (
                    existing_hash_doc.document_type.value
                    if hasattr(existing_hash_doc.document_type, "value")
                    else str(existing_hash_doc.document_type)
                )
                raise Exception(
                    f"this exact file has already been uploaded as document type '{existing_type}'"
                )

            new_version = 1
            existing_latest = self.docRepo.FindLatestByDoctorAndType(doc.id, doc_type)
            if existing_latest:
                new_version = int(existing_latest.version or 1) + 1

            try:
                doc_type_enum = DocumentType(doc_type)
            except Exception:
                raise Exception(f"unsupported document_type '{doc_type}'")

            doc_id = str(uuid.uuid4())
            storage_key = f"doctors/{doc.public_id}/documents/{doc_id}{val_res.extension}"

            stream.seek(0)
            try:
                file_url = self.storageProvider.upload(ctx, stream, storage_key, val_res.mime_type)
            except Exception as e:
                raise Exception(f"storage upload failed: {e}")

            try:
                self.docRepo.MarkPreviousVersionsNotLatest(doc.id, doc_type)
            except Exception:
                pass

            doc_entity = DoctorDocument(
                document_id=doc_id,
                doctor_id=str(doc.id),
                document_type=doc_type_enum,
                file_url=file_url,
                original_filename=val_res.original_filename,
                mime_type=val_res.mime_type,
                file_size=val_res.file_size,
                file_hash=val_res.file_hash,
                resolution_width=val_res.width,
                resolution_height=val_res.height,
                version=new_version,
                is_latest=True,
                ocr_status=OCRStatus.PENDING,
            )

            try:
                self.docRepo.Create(doc_entity)
            except Exception as e:
                raise Exception(f"failed to save document metadata: {e}")

            return self._to_response(doc_entity, doc.public_id)
        finally:
            if hasattr(file, "close"):
                try:
                    file.close()
                except Exception:
                    pass

    def GetDoctorDocuments(self, ctx, doctor_public_id):
        doc = self.doctorRepo.FindByPublicID(str(doctor_public_id))
        if not doc:
            raise Exception("doctor account not found")

        documents = self.docRepo.FindByDoctorID(doc.id)
        return [self._to_response(d, doc.public_id) for d in documents]

    def DeleteDocument(self, ctx, document_id, doctor_public_id):
        doc = self.doctorRepo.FindByPublicID(str(doctor_public_id))
        if not doc:
            raise Exception("doctor account not found")
        return self.docRepo.Delete(str(document_id), doc.id)
