from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
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

# When center calibration locks, we capture the current pupil coordinates and
# subtract them from subsequent points. This prevents small calibration bias
# from making the graph look "slightly up" even when the user is centered.
_center_offset_left = None
_center_offset_right = None

try:
    import sys
    import types

    # MediaPipe 0.10.14 pulls tensorflow via mediapipe.tasks; Face Mesh only needs solutions.
    sys.modules.setdefault("mediapipe.tasks", types.ModuleType("mediapipe.tasks"))
    sys.modules.setdefault("mediapipe.tasks.python", types.ModuleType("mediapipe.tasks.python"))

    from eye_tracking.fgi_eye_tracker import EyeTracker, EyeXYGraph
    tracker = EyeTracker()
    graph = EyeXYGraph(width=360, height=360, history=80)
    _graph_locked = False
except Exception as e:
    logger.error("Failed to load EyeTracker: %s", e)
    tracker = None
    graph = None
    _graph_locked = False

router = APIRouter(
    prefix="/api/v1/verification",
    tags=["verification", "liveness"]
)

class LivenessRequest(BaseModel):
    image: str
    reset: bool = False
    target: Optional[str] = None


def _decode_image(data_url: str):
    img_data = data_url
    if "," in img_data:
        img_data = img_data.split(",")[1]
    img_bytes = base64.b64decode(img_data)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)


def _jpeg_url(img, quality=80):
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


def _run_demo_frame(img, reset: bool = False, target: str = ""):
    """Call the existing EyeTracker + EyeXYGraph exactly like demo.py."""
    global _graph_locked
    global _center_offset_left, _center_offset_right
    with _tracker_lock:
        if reset:
            try:
                tracker.eyes.calibrator.reset()
            except Exception:
                pass
            graph.clear()
            _graph_locked = False
            _center_offset_left = None
            _center_offset_right = None

        frame = cv2.flip(img, 1)
        result = tracker.estimate(frame)

        if result.calib_ready and not _graph_locked:
            graph.clear()
            _graph_locked = True
            # Capture current coordinates as the "true center" reference.
            if getattr(result, "both_eyes_facing", False) and result.left_xy is not None and result.right_xy is not None:
                _center_offset_left = tuple(result.left_xy)
                _center_offset_right = tuple(result.right_xy)
            else:
                _center_offset_left = None
                _center_offset_right = None

        # If calib_ready happened before we got both eyes facing, capture the
        # center offset as soon as both eyes become available.
        if _graph_locked and _center_offset_left is None and _center_offset_right is None:
            if getattr(result, "both_eyes_facing", False) and result.left_xy is not None and result.right_xy is not None:
                _center_offset_left = tuple(result.left_xy)
                _center_offset_right = tuple(result.right_xy)

        if result.both_eyes_facing:
            # Apply center offset correction if available.
            if _center_offset_left is not None and _center_offset_right is not None and result.left_xy is not None and result.right_xy is not None:
                lx, ly = result.left_xy
                rx, ry = result.right_xy
                clx, cly = _center_offset_left
                crx, cry = _center_offset_right

                # Clamp to keep values inside [-1, 1] for the graph renderer.
                adj_left = (max(-1.0, min(1.0, lx - clx)), max(-1.0, min(1.0, ly - cly)))
                adj_right = (max(-1.0, min(1.0, rx - crx)), max(-1.0, min(1.0, ry - cry)))
                graph.push(adj_left, adj_right)
            else:
                graph.push(result.left_xy, result.right_xy)

        # Use real pupil direction so gaze challenges (left/right/top/bottom) work.
        direction_for_plot = getattr(result, "direction", "") or ""
        plot_view = graph.render(direction=direction_for_plot, target=target or "")
        return result, plot_view, direction_for_plot


@router.post("/liveness")
async def check_liveness(req: LivenessRequest):
    if not tracker:
        raise HTTPException(status_code=503, detail="Liveness service unavailable")

    try:
        img = _decode_image(req.image)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data")

        if float(np.mean(img)) < 12:
            return {
                "status": "success",
                "both_eyes_facing": False,
                "direction": "no_face",
                "face_detected": False,
                "calib_ready": False,
                "calib_progress": 0.0,
                "plot_image": None,
            }

        result, plot_view, direction_for_plot = await asyncio.to_thread(
            _run_demo_frame, img, req.reset, (req.target or "").strip().lower()
        )

        looked = (direction_for_plot or "").strip().lower()
        wanted = (req.target or "").strip().lower()
        return {
            "status": "success",
            "both_eyes_facing": bool(result.both_eyes_facing),
            "direction": direction_for_plot or getattr(result, "direction", "unknown"),
            "target": wanted or None,
            "target_hit": bool(wanted and looked == wanted and result.both_eyes_facing),
            "face_detected": bool(getattr(result, "face_detected", False)),
            "calib_ready": bool(getattr(result, "calib_ready", False)),
            "calib_progress": float(getattr(result, "calib_progress", 0.0) or 0.0),
            "left_xy": list(result.left_xy) if result.left_xy else None,
            "right_xy": list(result.right_xy) if result.right_xy else None,
            "plot_image": _jpeg_url(plot_view),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Liveness check failed")
        raise HTTPException(status_code=500, detail=str(e))


class LiveDocRequest(BaseModel):
    image: str
    step1_face: Optional[str] = None
    step3_faces: list[str] = []


@router.post("/live-doc")
async def live_doc_ocr(req: LiveDocRequest):
    """Proxy webcam frame to the existing OCR live_verify module (unflipped capture)."""
    import os
    import requests

    ocr_url = os.getenv("OCR_SERVICE_URL", "http://127.0.0.1:5001/api/v1/ocr")
    live_url = ocr_url.replace("/api/v1/ocr", "/api/v1/live_verify")

    def _call():
        payload = {
            "image": req.image,
            "step1_face": (req.step1_face or "").strip() or None,
            "step3_faces": req.step3_faces or [],
        }
        resp = requests.post(live_url, json=payload, timeout=180)
        try:
            body = resp.json()
        except Exception:
            body = {"error": resp.text[:300]}
        return resp.status_code, body

    try:
        code, data = await asyncio.to_thread(_call)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"OCR live_verify unreachable: {e}")

    if code >= 400:
        raise HTTPException(status_code=code, detail=data.get("error") or data.get("detail") or "live OCR failed")

    # Image URLs are already relative paths (e.g. /ocr_uploads/...) and will be
    # served by the portal's own /ocr_uploads static mount — no rewriting needed.
    return data
