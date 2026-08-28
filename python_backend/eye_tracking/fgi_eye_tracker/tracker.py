"""Realtime eye / gaze tracking — both eyes facing camera, anywhere in frame."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np

try:
    import torch
    _HAS_TORCH = bool(getattr(torch, "__file__", None)) and callable(getattr(torch, "device", None))
except Exception:
    torch = None
    _HAS_TORCH = False

from .face_eyes import FaceEyeEngine
from .preprocess import expand_box, face_to_tensor


@dataclass
class GazeResult:
    pitch: float
    yaw: float
    direction: str  # center|left|right|top|bottom|no_face|no_eyes|turn_to_camera
    face_box: Optional[Tuple[int, int, int, int]]
    face_detected: bool
    both_eyes_facing: bool
    weights_loaded: bool
    left_xy: Optional[Tuple[float, float]]
    right_xy: Optional[Tuple[float, float]]
    left_box: Optional[Tuple[int, int, int, int]]
    right_box: Optional[Tuple[int, int, int, int]]
    left_pupil_px: Optional[Tuple[int, int]]
    right_pupil_px: Optional[Tuple[int, int]]
    backend: str = "none"
    calib_ready: bool = False
    calib_progress: float = 0.0


class EyeTracker:
    """
    Track pupils and gaze direction only when BOTH eyes face the camera.

    Face may appear anywhere in the frame (MediaPipe mesh + iris; OpenCV fallback).
    Plotting should only consume left_xy/right_xy when both_eyes_facing is True.
    """

    def __init__(
        self,
        weight_path: Optional[str] = None,
        device: Optional[str] = None,
        center_thresh: float = 0.22,
        facing_thresh: float = 0.55,
        use_fgi_refine: bool = True,
    ):
        self.center_thresh = center_thresh
        self.use_fgi_refine = bool(use_fgi_refine and _HAS_TORCH)
        self.weights_loaded = False
        self._is_init_checkpoint = True
        self.model = None
        self.device = None

        self.eyes = FaceEyeEngine(
            facing_thresh=facing_thresh,
            center_thresh=center_thresh,
        )

        if not _HAS_TORCH:
            print("[EyeTracker] PyTorch unavailable — using MediaPipe pupil tracking only.")
            return

        try:
            from .fgi_net import FGI_Net
            self.device = torch.device(
                device or ("cuda" if torch.cuda.is_available() else "cpu")
            )
            self.model = FGI_Net(num_classes=2).to(self.device)
            self.model.eval()
        except Exception as exc:
            print(f"[EyeTracker] FGI-Net unavailable ({exc}) — MediaPipe pupil tracking only.")
            self.model = None
            self.device = None
            return

        default_w = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "weights",
            "fgi_net.pth",
        )
        path = weight_path or default_w
        if path and os.path.isfile(path):
            self._load_weights(path)
        else:
            print(f"[EyeTracker] No checkpoint at {path}.")

    def _load_weights(self, path: str) -> None:
        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        state = ckpt.get("state_dict", ckpt.get("model", ckpt))
        if isinstance(state, dict) and any(k.startswith("module.") for k in state):
            state = {k.replace("module.", "", 1): v for k, v in state.items()}
        self.model.load_state_dict(state, strict=False)
        meta = ckpt.get("meta") if isinstance(ckpt, dict) else None
        self.weights_loaded = True
        self._is_init_checkpoint = bool(
            isinstance(meta, dict) and meta.get("source") == "architecture_init"
        )
        print(f"[EyeTracker] Loaded weights from {path}")

    def close(self):
        self.eyes.close()

    def _empty(self, direction: str = "no_face", backend: str = "none") -> GazeResult:
        return GazeResult(
            pitch=0.0,
            yaw=0.0,
            direction=direction,
            face_box=None,
            face_detected=False,
            both_eyes_facing=False,
            weights_loaded=self.weights_loaded,
            left_xy=None,
            right_xy=None,
            left_box=None,
            right_box=None,
            left_pupil_px=None,
            right_pupil_px=None,
            backend=backend,
            calib_ready=self.eyes.calibrator.ready,
            calib_progress=self.eyes.calibrator.progress,
        )

    def estimate(self, frame_bgr: np.ndarray) -> GazeResult:
        h, w = frame_bgr.shape[:2]
        track = self.eyes.process(frame_bgr)

        if track.face_box is None:
            return self._empty("no_face", track.backend)

        left, right = track.left, track.right
        direction = track.direction
        both = track.both_eyes_facing

        # Optional FGI refine only when both eyes face camera + real weights
        pitch = yaw = 0.0
        if _HAS_TORCH and self.model is not None and both:
            x1, y1, x2, y2 = track.face_box
            fw, fh = x2 - x1, y2 - y1
            ex1, ey1, ex2, ey2 = expand_box(x1, y1, fw, fh, w, h, scale=1.25)
            crop = frame_bgr[ey1:ey2, ex1:ex2]
            if crop.size > 0:
                with torch.inference_mode():
                    tensor = face_to_tensor(crop)
                    batch = torch.from_numpy(tensor).unsqueeze(0).to(self.device)
                    out = self.model(batch)
                    pitch = float(out[0, 0].item())
                    yaw = float(out[0, 1].item())
                if (
                    self.use_fgi_refine
                    and self.weights_loaded
                    and not self._is_init_checkpoint
                    and direction == "center"
                ):
                    if abs(yaw) >= abs(pitch) and abs(yaw) > 0.12:
                        direction = "left" if yaw < 0 else "right"
                    elif abs(pitch) > 0.12:
                        direction = "top" if pitch < 0 else "bottom"

        # Only expose plottable xy when both eyes face the camera
        return GazeResult(
            pitch=pitch,
            yaw=yaw,
            direction=direction if both else track.direction,
            face_box=track.face_box,
            face_detected=True,
            both_eyes_facing=both,
            weights_loaded=self.weights_loaded,
            left_xy=(left.x, left.y) if (both and left) else None,
            right_xy=(right.x, right.y) if (both and right) else None,
            left_box=left.box if left else None,
            right_box=right.box if right else None,
            left_pupil_px=left.pupil_px if (both and left) else None,
            right_pupil_px=right.pupil_px if (both and right) else None,
            backend=track.backend,
            calib_ready=track.calib_ready,
            calib_progress=track.calib_progress,
        )

    def annotated_frame(self, frame_bgr: np.ndarray, result: GazeResult) -> np.ndarray:
        out = frame_bgr.copy()
        status_color = (80, 255, 160) if result.both_eyes_facing else (60, 60, 220)

        if result.face_box:
            x1, y1, x2, y2 = result.face_box
            cv2.rectangle(out, (x1, y1), (x2, y2), status_color, 2)

        if result.both_eyes_facing:
            for box, color, tag in [
                (result.left_box, (40, 160, 255), "L"),
                (result.right_box, (255, 160, 40), "R"),
            ]:
                if box:
                    cv2.rectangle(out, (box[0], box[1]), (box[2], box[3]), color, 1)
                    cv2.putText(
                        out, tag, (box[0], max(12, box[1] - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1,
                    )
            for pupil, color in [
                (result.left_pupil_px, (40, 160, 255)),
                (result.right_pupil_px, (255, 160, 40)),
            ]:
                if pupil:
                    cv2.circle(out, pupil, 4, color, -1)
                    cv2.circle(out, pupil, 6, (255, 255, 255), 1)

            label = f"Looking: {result.direction.upper()}"
            detail = ""
            if result.left_xy:
                detail += f"L({result.left_xy[0]:+.2f},{result.left_xy[1]:+.2f})  "
            if result.right_xy:
                detail += f"R({result.right_xy[0]:+.2f},{result.right_xy[1]:+.2f})"
            cv2.putText(out, label, (20, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (20, 20, 20), 3)
            cv2.putText(out, label, (20, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.85, status_color, 2)
            if detail:
                cv2.putText(out, detail.strip(), (20, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (230, 230, 230), 1)
            cv2.putText(
                out, "Both eyes facing camera — tracking",
                (20, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 1,
            )
            if not result.calib_ready:
                pct = int(result.calib_progress * 100)
                cv2.putText(
                    out,
                    f"Calibrating center… look straight ({pct}%)",
                    (20, 124),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (80, 200, 255),
                    1,
                )
        else:
            msg = {
                "no_face": "No face in frame — move into view",
                "no_eyes": "Eyes not detected — face the camera",
                "turn_to_camera": "Turn to face the camera (both eyes)",
            }.get(result.direction, "Face the camera with both eyes visible")
            cv2.putText(out, msg, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 3)
            cv2.putText(out, msg, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
            cv2.putText(
                out, "Plot updates only when BOTH eyes face the camera",
                (20, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1,
            )

        return out
