from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio
import base64
import logging
import threading
import warnings
import numpy as np
import cv2

warnings.filterwarnings("ignore", message="SymbolDatabase.GetPrototype")

logger = logging.getLogger(__name__)
_tracker_lock = threading.Lock()

try:
    from eye_tracking.fgi_eye_tracker import EyeTracker
    tracker = EyeTracker()
except Exception as e:
    logger.error("Failed to load EyeTracker: %s", e)
    tracker = None

router = APIRouter(
    prefix="/api/v1/verification",
    tags=["verification", "liveness"]
)

class LivenessRequest(BaseModel):
    image: str
    reset: bool = False

class DocFaceRequest(BaseModel):
    image: str


def _decode_image(data_url: str):
    img_data = data_url
    if "," in img_data:
        img_data = img_data.split(",")[1]
    img_bytes = base64.b64decode(img_data)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)


def _estimate(img, reset: bool = False):
    with _tracker_lock:
        if reset:
            try:
                tracker.eyes.calibrator.reset()
            except Exception:
                pass
        return tracker.estimate(img)


@router.post("/liveness")
async def check_liveness(req: LivenessRequest):
    if not tracker:
        raise HTTPException(status_code=503, detail="Liveness service unavailable")

    try:
        img = _decode_image(req.image)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data")

        # Skip near-black warmup frames so liveness cannot "pass" instantly.
        if float(np.mean(img)) < 12:
            return {
                "status": "success",
                "both_eyes_facing": False,
                "direction": "no_face",
                "face_detected": False,
                "face_box": None,
            }

        result = await asyncio.to_thread(_estimate, img, req.reset)

        face_box = getattr(result, "face_box", None)
        if face_box is not None:
            face_box = [int(v) for v in face_box]

        return {
            "status": "success",
            "both_eyes_facing": bool(result.both_eyes_facing),
            "direction": getattr(result, "direction", "unknown"),
            "face_detected": bool(getattr(result, "face_detected", False)),
            "face_box": face_box,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Liveness check failed")
        raise HTTPException(status_code=500, detail=str(e))


def _detect_face_on_document(img):
    """Use OpenCV Haar cascade to find faces in a document image held in front of camera."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = None
    if hasattr(cv2, "CascadeClassifier"):
        for xml in [
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml",
            cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml",
        ]:
            cc = cv2.CascadeClassifier(xml)
            if not cc.empty():
                face_cascade = cc
                break
    if face_cascade is None:
        return None, None
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
    if len(faces) == 0:
        return None, None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    pad = int(0.15 * max(w, h))
    y1 = max(0, y - pad); x1 = max(0, x - pad)
    y2 = min(img.shape[0], y + h + pad); x2 = min(img.shape[1], x + w + pad)
    crop = img[y1:y2, x1:x2]
    crop_resized = cv2.resize(crop, (112, 112))
    return crop_resized, [int(x1), int(y1), int(x2), int(y2)]


@router.post("/capture-doc-face")
async def capture_doc_face(req: DocFaceRequest):
    """Extract face from ID card held in front of camera."""
    try:
        img = _decode_image(req.image)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image")
        if float(np.mean(img)) < 12:
            return {"face_detected": False, "face_image": None, "face_box": None}

        face_crop, face_box = await asyncio.to_thread(_detect_face_on_document, img)
        if face_crop is None:
            return {"face_detected": False, "face_image": None, "face_box": None}

        _, buf = cv2.imencode(".jpg", face_crop)
        b64 = base64.b64encode(buf).decode()
        return {
            "face_detected": True,
            "face_image": f"data:image/jpeg;base64,{b64}",
            "face_box": face_box,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Doc face capture failed")
        raise HTTPException(status_code=500, detail=str(e))
