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
    image: str  # Base64 encoded image data URL (e.g., data:image/jpeg;base64,...)
    reset: bool = False


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
        img_data = req.image
        if "," in img_data:
            img_data = img_data.split(",")[1]

        img_bytes = base64.b64decode(img_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

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
