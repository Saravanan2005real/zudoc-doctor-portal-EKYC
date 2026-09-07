from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

# Step 4.2 liveness is WebGazer in the browser (same localhost).
# Do not load FGI-Net / MediaPipe EyeTracker here — that caused the
# "PyTorch unavailable" + TFLite feedback warnings on startup.

router = APIRouter(
    prefix="/api/v1/verification",
    tags=["verification", "liveness"]
)

class LivenessRequest(BaseModel):
    image: str
    reset: bool = False
    target: Optional[str] = None


@router.post("/liveness")
async def check_liveness(req: LivenessRequest):
    """Kept for API compatibility. Step 4.2 runs WebGazer in the browser."""
    return {
        "status": "success",
        "backend": "webgazer",
        "both_eyes_facing": False,
        "direction": "client_webgazer",
        "target": (req.target or "").strip().lower() or None,
        "target_hit": False,
        "face_detected": False,
        "calib_ready": False,
        "calib_progress": 0.0,
        "left_xy": None,
        "right_xy": None,
        "plot_image": None,
        "message": "Liveness is handled by WebGazer in the portal (same localhost).",
    }


class LiveDocRequest(BaseModel):
    image: str
    step1_face: Optional[str] = None
    step3_faces: list[str] = []


@router.post("/live-doc")
async def live_doc_ocr(req: LiveDocRequest):
    """Run live ID-hold OCR + face extract."""
    import httpx
    
    payload = {
        "image": req.image,
        "step1_face": (req.step1_face or "").strip() or None,
        "step3_faces": req.step3_faces or [],
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post("http://ocr_engine:5001/api/v1/live_verify", json=payload, timeout=30.0)
            code = resp.status_code
            data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"OCR live_verify failed: {e}")

    if code >= 400:
        raise HTTPException(status_code=code, detail=data.get("error") or data.get("detail") or "live OCR failed")

    return data
