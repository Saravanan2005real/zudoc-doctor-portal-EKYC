"""Face crop + ImageNet-style normalize for FGI-Net (224x224)."""

from __future__ import annotations

import cv2
import numpy as np

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def detect_largest_face(frame_bgr: np.ndarray, cascade) -> tuple[int, int, int, int] | None:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
    return int(x), int(y), int(w), int(h)


def expand_box(x, y, w, h, frame_w, frame_h, scale: float = 1.35):
    cx, cy = x + w / 2.0, y + h / 2.0
    nw, nh = w * scale, h * scale
    x1 = max(0, int(cx - nw / 2))
    y1 = max(0, int(cy - nh / 2))
    x2 = min(frame_w, int(cx + nw / 2))
    y2 = min(frame_h, int(cy + nh / 2))
    return x1, y1, x2, y2


def face_to_tensor(face_bgr: np.ndarray, size: int = 224) -> np.ndarray:
    """Return float32 CHW tensor normalized for the network."""
    rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_LINEAR)
    x = rgb.astype(np.float32) / 255.0
    x = (x - IMAGENET_MEAN) / IMAGENET_STD
    x = np.transpose(x, (2, 0, 1))  # CHW
    return np.ascontiguousarray(x)
