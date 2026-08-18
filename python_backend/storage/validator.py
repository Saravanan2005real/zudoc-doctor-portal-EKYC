import os
import hashlib
import mimetypes

try:
    from PIL import Image
except ImportError:
    Image = None

class FileValidationResult:
    def __init__(self, original_filename, mime_type, extension, file_size, file_hash, width=None, height=None):
        self.original_filename = original_filename
        self.mime_type = mime_type
        self.extension = extension
        self.file_size = file_size
        self.file_hash = file_hash
        self.width = width
        self.height = height

class FileValidator:
    def __init__(self, max_size_bytes: int = 25 * 1024 * 1024, min_image_dimension: int = 200):
        self.max_size_bytes = max_size_bytes if max_size_bytes > 0 else 10 * 1024 * 1024
        self.min_image_dimension = min_image_dimension if min_image_dimension > 0 else 300

    def validate(self, file, original_filename: str, declared_size: int) -> FileValidationResult:
        ext = os.path.splitext(original_filename)[1].lower()
        blocked_extensions = {".exe", ".sh", ".bat", ".cmd", ".js", ".py", ".php", ".zip", ".tar", ".gz", ".rar", ".7z"}
        if ext in blocked_extensions:
            raise ValueError(f"file type '{ext}' is strictly prohibited for security reasons")

        allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}
        if ext not in allowed_extensions:
            raise ValueError(f"unsupported file extension '{ext}'. Only PDF, JPG, JPEG, and PNG files are allowed")

        if declared_size > self.max_size_bytes:
            raise ValueError(f"file size exceeds maximum limit of {self.max_size_bytes // (1024 * 1024)} MB")

        buffer = file.read(512)
        detected_mime = mimetypes.guess_type(original_filename)[0] or "application/octet-stream"
        
        if ext == ".pdf" and "pdf" not in detected_mime and "application/octet-stream" not in detected_mime:
            if len(buffer) >= 4 and buffer[:4] == b"%PDF":
                detected_mime = "application/pdf"
            else:
                raise ValueError("file content does not match valid PDF format")

        allowed_mimes = {"application/pdf", "image/jpeg", "image/jpg", "image/png"}
        if detected_mime not in allowed_mimes and not detected_mime.startswith("image/"):
            raise ValueError(f"invalid file MIME type '{detected_mime}'")

        file.seek(0)
        hasher = hashlib.sha256()
        size = 0
        while chunk := file.read(8192):
            hasher.update(chunk)
            size += len(chunk)

        if size > self.max_size_bytes:
            raise ValueError(f"file size {size} bytes exceeds maximum limit of {self.max_size_bytes // (1024 * 1024)} MB")

        file_hash = hasher.hexdigest()

        width_ptr, height_ptr = None, None
        if detected_mime.startswith("image/"):
            if Image is None:
                raise ValueError("image validation requires Pillow. Install with: pip install Pillow")
            file.seek(0)
            try:
                with Image.open(file) as img:
                    w, h = img.size
                    if w < self.min_image_dimension or h < self.min_image_dimension:
                        raise ValueError(
                            f"image resolution {w}x{h} is below minimum required resolution of "
                            f"{self.min_image_dimension}x{self.min_image_dimension} pixels"
                        )
                    width_ptr, height_ptr = w, h
            except Exception as e:
                if isinstance(e, ValueError):
                    raise e
                raise ValueError(f"unable to read image file: {e}")

        file.seek(0)

        return FileValidationResult(
            original_filename=original_filename,
            mime_type=detected_mime,
            extension=ext,
            file_size=size,
            file_hash=file_hash,
            width=width_ptr,
            height=height_ptr
        )
