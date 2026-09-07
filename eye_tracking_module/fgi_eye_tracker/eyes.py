"""Per-eye ROI + pupil (x, y) extraction for gaze direction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class EyeSample:
    """Normalized pupil position in eye box: x,y in [-1, 1] (0 = center)."""

    x: float
    y: float
    box: tuple[int, int, int, int]  # x1,y1,x2,y2 in frame coords
    pupil_px: tuple[int, int]  # absolute pixel in frame


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def eye_rois_from_face(
    face_xywh: tuple[int, int, int, int],
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    """
    Geometric left/right eye boxes inside a face bbox (frame coords).
    Assumes mirrored selfie view: image-left = viewer's left eye.
    """
    fx, fy, fw, fh = face_xywh
    # Left eye (image left)
    lx1 = int(fx + fw * 0.12)
    ly1 = int(fy + fh * 0.22)
    lx2 = int(fx + fw * 0.48)
    ly2 = int(fy + fh * 0.48)
    # Right eye (image right)
    rx1 = int(fx + fw * 0.52)
    ry1 = int(fy + fh * 0.22)
    rx2 = int(fx + fw * 0.88)
    ry2 = int(fy + fh * 0.48)
    return (lx1, ly1, lx2, ly2), (rx1, ry1, rx2, ry2)


def find_pupil_in_roi(frame_bgr: np.ndarray, box: tuple[int, int, int, int]) -> Optional[EyeSample]:
    x1, y1, x2, y2 = box
    if x2 - x1 < 12 or y2 - y1 < 10:
        return None
    roi = frame_bgr[y1:y2, x1:x2]
    if roi.size == 0:
        return None

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    # Emphasize dark pupil
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    gray = clahe.apply(gray)

    # Ignore eyebrows: keep a taller band so looking up/down still moves the blob
    h, w = gray.shape
    band = gray[int(h * 0.12) : int(h * 0.92), int(w * 0.1) : int(w * 0.9)]
    if band.size == 0:
        return None

    # Darkest percentile blob
    thr = int(np.percentile(band, 18))
    mask = (band <= thr).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    y_off = h * 0.12
    x_off = w * 0.1
    if contours:
        c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(c) >= 4:
            m = cv2.moments(c)
            if m["m00"] > 0:
                px = m["m10"] / m["m00"] + x_off
                py = m["m01"] / m["m00"] + y_off
            else:
                px, py = w / 2.0, h / 2.0
        else:
            min_loc = cv2.minMaxLoc(band)[2]
            px = min_loc[0] + x_off
            py = min_loc[1] + y_off
    else:
        min_loc = cv2.minMaxLoc(band)[2]
        px = min_loc[0] + x_off
        py = min_loc[1] + y_off

    # Normalize to [-1, 1] relative to eye box center
    nx = _clamp((px / max(w - 1, 1)) * 2.0 - 1.0, -1.0, 1.0)
    ny = _clamp((py / max(h - 1, 1)) * 2.0 - 1.0, -1.0, 1.0)

    abs_x = int(x1 + px)
    abs_y = int(y1 + py)
    return EyeSample(x=float(nx), y=float(ny), box=box, pupil_px=(abs_x, abs_y))


def classify_direction(
    left: Optional[EyeSample],
    right: Optional[EyeSample],
    center_thresh: float = 0.22,
    vertical_thresh: float = 0.12,
    vertical_gain: float = 1.85,
) -> str:
    """
    Predict looking direction from pupil offsets.

    Left/right keep the original horizontal threshold behavior.
    Top/bottom use a vertical gain because iris y-range inside the eye is smaller.
    """
    xs, ys = [], []
    if left is not None:
        xs.append(left.x)
        ys.append(left.y)
    if right is not None:
        xs.append(right.x)
        ys.append(right.y)
    if not xs:
        return "no_eyes"

    ax = float(np.mean(xs))
    ay = float(np.mean(ys))
    ay_cmp = ay * vertical_gain  # decision only — does not change plotted (x,y)

    # Still looking near center
    if abs(ax) < center_thresh and abs(ay) < vertical_thresh:
        return "center"

    # Strong horizontal → keep left/right as before (do not disturb)
    if abs(ax) >= center_thresh and abs(ax) >= abs(ay_cmp):
        return "left" if ax < 0 else "right"

    # Vertical wins when amplified y dominates or clear vertical signal
    if abs(ay) >= vertical_thresh and abs(ay_cmp) >= abs(ax):
        return "top" if ay < 0 else "bottom"

    # Fallbacks
    if abs(ax) >= center_thresh:
        return "left" if ax < 0 else "right"
    if abs(ay) >= vertical_thresh:
        return "top" if ay < 0 else "bottom"
    return "center"
