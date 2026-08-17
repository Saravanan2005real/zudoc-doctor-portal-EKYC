from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import base64
import numpy as np
import cv2

# Import the EyeTracker from our newly moved eye_tracking module
try:
    from eye_tracking.fgi_eye_tracker import EyeTracker
    tracker = EyeTracker()
except Exception as e:
    import logging
    logging.getLogger(__name__).error(f"Failed to load EyeTracker: {e}")
    tracker = None

router = APIRouter(
    prefix="/api/v1/verification",
    tags=["verification", "liveness"]
)

class LivenessRequest(BaseModel):
    image: str  # Base64 encoded image data URL (e.g., data:image/jpeg;base64,...)

@router.post("/liveness")
async def check_liveness(req: LivenessRequest):
    if not tracker:
        raise HTTPException(status_code=503, detail="Liveness service unavailable")

    try:
        # Extract base64 part
        img_data = req.image
        if "," in img_data:
            img_data = img_data.split(",")[1]
            
        img_bytes = base64.b64decode(img_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data")

        # Run eye tracking
        result = tracker.estimate(img)
        
        return {
            "status": "success",
            "both_eyes_facing": result.both_eyes_facing,
            "direction": result.direction if hasattr(result, 'direction') else "unknown"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
