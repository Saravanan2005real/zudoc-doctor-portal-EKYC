"""Lightweight live-frame quality checks for Step 4.1 (no extra models)."""

from __future__ import annotations

import cv2
import numpy as np


def assess_live_frame(img_bgr) -> dict:
    if img_bgr is None or getattr(img_bgr, "size", 0) == 0:
        return {
            "ok": False,
            "brightness": 0.0,
            "sharpness": 0.0,
            "lighting_ok": False,
            "sharp_ok": False,
            "resolution_ok": False,
            "width": 0,
            "height": 0,
        }
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    lighting_ok = 50.0 <= brightness <= 210.0
    sharp_ok = sharpness >= 35.0
    resolution_ok = w >= 480 and h >= 360
    return {
        "ok": bool(lighting_ok and sharp_ok and resolution_ok),
        "brightness": round(brightness, 1),
        "sharpness": round(sharpness, 1),
        "lighting_ok": lighting_ok,
        "sharp_ok": sharp_ok,
        "resolution_ok": resolution_ok,
        "width": int(w),
        "height": int(h),
    }


def ocr_fields_usable(parsed: dict | None) -> bool:
    parsed = parsed or {}
    if parsed.get("aadhaar_number") or parsed.get("pan_number"):
        return True
    name = str(parsed.get("name") or "").strip()
    return bool(name) and str(parsed.get("document_type") or "").upper() in ("AADHAAR", "PAN")
