"""Auto-center calibration — removes resting upward/side bias on the (x,y) plot."""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from .eyes import EyeSample, _clamp


class CenterCalibrator:
    """
    Learns each eye's resting (x, y) while the user faces the camera,
    then subtracts that offset so looking-center sits at (0, 0).

    Does not change left/right sensitivity — only recenters the origin.
    """

    def __init__(self, samples_needed: int = 30, max_std: float = 0.10):
        self.samples_needed = samples_needed
        self.max_std = max_std
        self.ready = False
        self.left_bias = (0.0, 0.0)
        self.right_bias = (0.0, 0.0)
        self._buf: List[Tuple[float, float, float, float]] = []

    def reset(self) -> None:
        self.ready = False
        self.left_bias = (0.0, 0.0)
        self.right_bias = (0.0, 0.0)
        self._buf.clear()

    def update(self, left: Optional[EyeSample], right: Optional[EyeSample], both_facing: bool) -> None:
        if self.ready or not both_facing or left is None or right is None:
            return

        self._buf.append((left.x, left.y, right.x, right.y))
        if len(self._buf) < self.samples_needed:
            return

        arr = np.asarray(self._buf[-self.samples_needed :], dtype=np.float32)
        std = arr.std(axis=0)
        mean = arr.mean(axis=0)

        # Stable + roughly frontal gaze → lock as center origin
        stable = bool(np.all(std <= self.max_std))
        near_center_x = abs(float(mean[0])) < 0.40 and abs(float(mean[2])) < 0.40
        if stable and near_center_x:
            self.left_bias = (float(mean[0]), float(mean[1]))
            self.right_bias = (float(mean[2]), float(mean[3]))
            self.ready = True
            print(
                f"[Calibrator] Center locked  "
                f"L bias=({self.left_bias[0]:+.2f},{self.left_bias[1]:+.2f})  "
                f"R bias=({self.right_bias[0]:+.2f},{self.right_bias[1]:+.2f})"
            )
        else:
            # Slide window and keep collecting
            self._buf = self._buf[-self.samples_needed :]

    def apply(
        self, left: Optional[EyeSample], right: Optional[EyeSample]
    ) -> tuple[Optional[EyeSample], Optional[EyeSample]]:
        # While learning, use running mean as soft bias so plot doesn't sit "up"
        if not self.ready and len(self._buf) >= 8:
            arr = np.asarray(self._buf, dtype=np.float32)
            mean = arr.mean(axis=0)
            lb = (float(mean[0]), float(mean[1]))
            rb = (float(mean[2]), float(mean[3]))
        else:
            lb, rb = self.left_bias, self.right_bias

        return self._shift(left, lb), self._shift(right, rb)

    @staticmethod
    def _shift(sample: Optional[EyeSample], bias: Tuple[float, float]) -> Optional[EyeSample]:
        if sample is None:
            return None
        bx, by = bias
        return EyeSample(
            x=_clamp(sample.x - bx, -1.0, 1.0),
            y=_clamp(sample.y - by, -1.0, 1.0),
            box=sample.box,
            pupil_px=sample.pupil_px,
        )

    @property
    def progress(self) -> float:
        if self.ready:
            return 1.0
        return min(1.0, len(self._buf) / max(self.samples_needed, 1))
