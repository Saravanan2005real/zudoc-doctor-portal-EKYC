"""
Robust face + both-eyes pupil tracking anywhere in the frame.

Primary: MediaPipe Face Mesh (iris) — works regardless of face position.
Fallback: OpenCV Haar face + geometric eye ROIs + dark-pupil search.
Tracking / plotting is gated on both_eyes_facing_camera == True.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np

from .calibrate import CenterCalibrator
from .eyes import EyeSample, classify_direction, eye_rois_from_face, find_pupil_in_roi


# MediaPipe Face Mesh iris / eye corner indices (with refine_landmarks=True)
_LEFT_IRIS = [468, 469, 470, 471, 472]
_RIGHT_IRIS = [473, 474, 475, 476, 477]
_LEFT_EYE_CORNERS = (33, 133)   # outer, inner
_RIGHT_EYE_CORNERS = (362, 263)
_LEFT_EYE_LIDS = (159, 145)     # upper, lower
_RIGHT_EYE_LIDS = (386, 374)
_NOSE_TIP = 1
_CHIN = 152
_FOREHEAD = 10
_LEFT_EYE_OVAL = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
_RIGHT_EYE_OVAL = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]


@dataclass
class BothEyesTrack:
    left: Optional[EyeSample]
    right: Optional[EyeSample]
    face_box: Optional[Tuple[int, int, int, int]]
    both_eyes_facing: bool
    direction: str
    backend: str  # mediapipe | opencv
    calib_ready: bool = False
    calib_progress: float = 0.0


def _lm_xy(lm, w: int, h: int) -> Tuple[float, float]:
    return lm.x * w, lm.y * h


def _eye_sample_from_iris(
    iris_ids,
    corner_ids,
    lid_ids,
    oval_ids,
    lms,
    w: int,
    h: int,
) -> Optional[EyeSample]:
    iris_pts = np.array([_lm_xy(lms[i], w, h) for i in iris_ids], dtype=np.float32)
    c0 = np.array(_lm_xy(lms[corner_ids[0]], w, h), dtype=np.float32)
    c1 = np.array(_lm_xy(lms[corner_ids[1]], w, h), dtype=np.float32)
    u = np.array(_lm_xy(lms[lid_ids[0]], w, h), dtype=np.float32)
    d = np.array(_lm_xy(lms[lid_ids[1]], w, h), dtype=np.float32)
    oval = np.array([_lm_xy(lms[i], w, h) for i in oval_ids], dtype=np.float32)

    pupil = iris_pts.mean(axis=0)
    oval_center = oval.mean(axis=0)

    # Eye box from corners + lids with padding (for drawing only)
    xs = [c0[0], c1[0], u[0], d[0], pupil[0]]
    ys = [c0[1], c1[1], u[1], d[1], pupil[1]]
    pad_x = max(6.0, 0.25 * abs(c1[0] - c0[0]))
    pad_y = max(4.0, 0.55 * abs(d[1] - u[1]))
    x1 = int(max(0, min(xs) - pad_x))
    y1 = int(max(0, min(ys) - pad_y))
    x2 = int(min(w - 1, max(xs) + pad_x))
    y2 = int(min(h - 1, max(ys) + pad_y))
    if x2 - x1 < 8 or y2 - y1 < 6:
        return None

    # Horizontal: eye corners (preserves left/right)
    mid_x = float((c0[0] + c1[0]) * 0.5)
    half_w = float(abs(c1[0] - c0[0]) * 0.5) + 1e-6
    nx = float(np.clip((pupil[0] - mid_x) / half_w, -1.0, 1.0))

    # Vertical: iris vs full eye-oval center (lid midpoint alone sits too low → upward bias)
    half_h = float(abs(d[1] - u[1]) * 0.5) + 1e-6
    ny = float(np.clip((pupil[1] - float(oval_center[1])) / half_h, -1.0, 1.0))

    # Openness (EAR-like): reject nearly closed eyes
    eye_open = float(np.linalg.norm(u - d) / (np.linalg.norm(c0 - c1) + 1e-6))
    if eye_open < 0.12:
        return None

    return EyeSample(
        x=nx,
        y=ny,
        box=(x1, y1, x2, y2),
        pupil_px=(int(pupil[0]), int(pupil[1])),
    )


def _facing_camera_score(lms, w: int, h: int) -> float:
    """
    Higher = more frontal.
    Uses eye-span symmetry and nose centered between eyes.
    """
    lo = np.array(_lm_xy(lms[_LEFT_EYE_CORNERS[0]], w, h))
    li = np.array(_lm_xy(lms[_LEFT_EYE_CORNERS[1]], w, h))
    ri = np.array(_lm_xy(lms[_RIGHT_EYE_CORNERS[0]], w, h))
    ro = np.array(_lm_xy(lms[_RIGHT_EYE_CORNERS[1]], w, h))
    nose = np.array(_lm_xy(lms[_NOSE_TIP], w, h))

    left_mid = (lo + li) / 2.0
    right_mid = (ri + ro) / 2.0
    eyes_mid = (left_mid + right_mid) / 2.0
    inter_ocular = float(np.linalg.norm(right_mid - left_mid)) + 1e-6

    # Nose should sit near horizontal midpoint of eyes when facing camera
    nose_offset = abs(float(nose[0] - eyes_mid[0])) / inter_ocular
    # Both eyes similar width
    left_w = float(np.linalg.norm(li - lo)) + 1e-6
    right_w = float(np.linalg.norm(ro - ri)) + 1e-6
    width_ratio = min(left_w, right_w) / max(left_w, right_w)

    # Score in [0, 1]
    frontal = width_ratio * float(np.clip(1.0 - nose_offset * 1.8, 0.0, 1.0))
    return frontal


class FaceEyeEngine:
    """Detect face anywhere in frame; require both eyes facing camera to track."""

    def __init__(self, facing_thresh: float = 0.55, center_thresh: float = 0.22):
        self.facing_thresh = facing_thresh
        self.center_thresh = center_thresh
        self.calibrator = CenterCalibrator(samples_needed=30, max_std=0.10)
        self._mp_mesh = None
        self._mp = None
        try:
            import mediapipe as mp

            self._mp = mp
            self._mp_mesh = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,  # iris landmarks
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            print("[FaceEyeEngine] MediaPipe Face Mesh + iris enabled")
        except Exception as e:
            print(f"[FaceEyeEngine] MediaPipe unavailable ({e}); using OpenCV fallback")

        # Haar is fallback only. OpenCV 5 wheels dropped CascadeClassifier.
        self.face_cascade = None
        self._cascade_ok = False
        if hasattr(cv2, "CascadeClassifier"):
            cascade_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "data",
                "haarcascade_frontalface_default.xml",
            )
            if not os.path.isfile(cascade_path):
                haar_dir = getattr(cv2, "data", None)
                haar_dir = getattr(haar_dir, "haarcascades", "") if haar_dir else ""
                cascade_path = os.path.join(haar_dir, "haarcascade_frontalface_default.xml")
            try:
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                self._cascade_ok = bool(self.face_cascade and not self.face_cascade.empty())
            except Exception as e:
                print(f"[FaceEyeEngine] Haar cascade unavailable ({e})")
        if not self._cascade_ok:
            print("[FaceEyeEngine] OpenCV Haar fallback disabled (MediaPipe is primary)")

    def close(self):
        if self._mp_mesh is not None:
            self._mp_mesh.close()

    def _finalize(
        self,
        left: Optional[EyeSample],
        right: Optional[EyeSample],
        face_box,
        both: bool,
        direction_if_not_both: str,
        backend: str,
    ) -> BothEyesTrack:
        # Learn / apply center bias so resting gaze is not stuck upward
        self.calibrator.update(left, right, both)
        left_c, right_c = self.calibrator.apply(left, right)
        if not both:
            return BothEyesTrack(
                left_c,
                right_c,
                face_box,
                False,
                direction_if_not_both,
                backend,
                self.calibrator.ready,
                self.calibrator.progress,
            )
        direction = classify_direction(left_c, right_c, center_thresh=self.center_thresh)
        return BothEyesTrack(
            left_c,
            right_c,
            face_box,
            True,
            direction,
            backend,
            self.calibrator.ready,
            self.calibrator.progress,
        )

    def process(self, frame_bgr: np.ndarray) -> BothEyesTrack:
        if self._mp_mesh is not None:
            track = self._process_mediapipe(frame_bgr)
            if track.face_box is not None or not self._cascade_ok:
                return track
        if self._cascade_ok:
            return self._process_opencv(frame_bgr)
        return BothEyesTrack(None, None, None, False, "no_face", "none")

    def _process_mediapipe(self, frame_bgr: np.ndarray) -> BothEyesTrack:
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        res = self._mp_mesh.process(rgb)
        if not res.multi_face_landmarks:
            return BothEyesTrack(None, None, None, False, "no_face", "mediapipe")

        lms = res.multi_face_landmarks[0].landmark
        # Need iris landmarks (468+)
        if len(lms) < 478:
            return BothEyesTrack(None, None, None, False, "no_eyes", "mediapipe")

        # Face box from all landmarks — works anywhere in frame
        xs = [lm.x * w for lm in lms]
        ys = [lm.y * h for lm in lms]
        face_box = (
            int(max(0, min(xs))),
            int(max(0, min(ys))),
            int(min(w - 1, max(xs))),
            int(min(h - 1, max(ys))),
        )

        left = _eye_sample_from_iris(
            _LEFT_IRIS, _LEFT_EYE_CORNERS, _LEFT_EYE_LIDS, _LEFT_EYE_OVAL, lms, w, h
        )
        right = _eye_sample_from_iris(
            _RIGHT_IRIS, _RIGHT_EYE_CORNERS, _RIGHT_EYE_LIDS, _RIGHT_EYE_OVAL, lms, w, h
        )

        facing = _facing_camera_score(lms, w, h) >= self.facing_thresh
        both = left is not None and right is not None and facing

        if not both:
            if left is None and right is None:
                direction = "no_eyes"
            elif not facing:
                direction = "turn_to_camera"
            else:
                direction = "turn_to_camera"
            return self._finalize(left, right, face_box, False, direction, "mediapipe")

        return self._finalize(left, right, face_box, True, "center", "mediapipe")

    def _process_opencv(self, frame_bgr: np.ndarray) -> BothEyesTrack:
        h, w = frame_bgr.shape[:2]
        # Multi-scale detection so face can be anywhere / any size
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.08,
            minNeighbors=4,
            minSize=(40, 40),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )
        if len(faces) == 0:
            return BothEyesTrack(None, None, None, False, "no_face", "opencv")

        fx, fy, fw, fh = max(faces, key=lambda r: r[2] * r[3])
        face = (int(fx), int(fy), int(fw), int(fh))
        face_box = (face[0], face[1], face[0] + face[2], face[1] + face[3])
        left_box, right_box = eye_rois_from_face(face)
        left = find_pupil_in_roi(frame_bgr, left_box)
        right = find_pupil_in_roi(frame_bgr, right_box)

        both = left is not None and right is not None
        if not both:
            return self._finalize(left, right, face_box, False, "turn_to_camera", "opencv")
        return self._finalize(left, right, face_box, True, "center", "opencv")