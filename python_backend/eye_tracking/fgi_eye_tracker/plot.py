"""Live (x, y) graph canvas for left and right eye pupil positions."""

from __future__ import annotations

from collections import deque
from typing import Deque, Optional, Tuple

import cv2
import numpy as np


Point = Tuple[float, float]


class EyeXYGraph:
    """
    Draws a Cartesian plot of normalized pupil (x, y) in [-1, 1]
    for left eye (blue) and right eye (orange), with short trails.
    """

    def __init__(self, width: int = 520, height: int = 520, history: int = 60):
        self.width = width
        self.height = height
        self.left_hist: Deque[Point] = deque(maxlen=history)
        self.right_hist: Deque[Point] = deque(maxlen=history)
        self.margin = 48

    def push(
        self,
        left_xy: Optional[Point],
        right_xy: Optional[Point],
    ) -> None:
        if left_xy is not None:
            self.left_hist.append(left_xy)
        if right_xy is not None:
            self.right_hist.append(right_xy)

    def clear(self) -> None:
        self.left_hist.clear()
        self.right_hist.clear()

    def _to_pixel(self, x: float, y: float) -> tuple[int, int]:
        # x: -1..1 → left..right ; y: -1..1 top..bottom (screen y grows down)
        m = self.margin
        usable_w = self.width - 2 * m
        usable_h = self.height - 2 * m
        px = int(m + (x + 1.0) * 0.5 * usable_w)
        py = int(m + (y + 1.0) * 0.5 * usable_h)
        return px, py

    def render(self, direction: str = "", target: str = "") -> np.ndarray:
        canvas = np.full((self.height, self.width, 3), 28, dtype=np.uint8)
        m = self.margin

        # Plot background
        cv2.rectangle(
            canvas,
            (m, m),
            (self.width - m, self.height - m),
            (45, 45, 45),
            -1,
        )

        # Grid
        for t in (-1.0, -0.5, 0.0, 0.5, 1.0):
            p1 = self._to_pixel(t, -1.0)
            p2 = self._to_pixel(t, 1.0)
            color = (70, 70, 70) if t != 0 else (110, 110, 110)
            cv2.line(canvas, p1, p2, color, 1)
            q1 = self._to_pixel(-1.0, t)
            q2 = self._to_pixel(1.0, t)
            cv2.line(canvas, q1, q2, color, 1)

        # Axes labels
        cv2.putText(canvas, "Eye (x, y) graph", (m, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (230, 230, 230), 2)
        cv2.putText(canvas, "LEFT", (m, self.height - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 180, 80), 2)
        cv2.putText(canvas, "RIGHT", (m + 80, self.height - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 180, 255), 2)
        cv2.putText(canvas, "-x", (m - 28, self.height // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
        cv2.putText(canvas, "+x", (self.width - m + 4, self.height // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
        cv2.putText(canvas, "-y top", (self.width // 2 - 30, m - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
        cv2.putText(canvas, "+y bottom", (self.width // 2 - 40, self.height - m + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

        # Quadrant hints
        for label, pos in [
            ("LEFT", self._to_pixel(-0.7, 0.0)),
            ("RIGHT", self._to_pixel(0.55, 0.0)),
            ("TOP", self._to_pixel(-0.08, -0.7)),
            ("BOTTOM", self._to_pixel(-0.12, 0.7)),
            ("CENTER", self._to_pixel(-0.12, -0.08)),
        ]:
            cv2.putText(canvas, label, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.4, (90, 90, 90), 1)

        def draw_trail(hist: Deque[Point], color_bgr, current_radius: int = 8):
            pts = list(hist)
            for i in range(1, len(pts)):
                a = self._to_pixel(*pts[i - 1])
                b = self._to_pixel(*pts[i])
                cv2.line(canvas, a, b, color_bgr, 2)
            if pts:
                p = self._to_pixel(*pts[-1])
                cv2.circle(canvas, p, current_radius, color_bgr, -1)
                cv2.circle(canvas, p, current_radius + 2, (255, 255, 255), 1)
                cv2.putText(
                    canvas,
                    f"({pts[-1][0]:+.2f},{pts[-1][1]:+.2f})",
                    (p[0] + 10, p[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    color_bgr,
                    1,
                )

        # Left = orange-ish, Right = blue-ish (BGR)
        draw_trail(self.left_hist, (40, 160, 255))
        draw_trail(self.right_hist, (255, 160, 40))

        target_xy = {
            "left": (-0.75, 0.0),
            "right": (0.75, 0.0),
            "top": (0.0, -0.75),
            "bottom": (0.0, 0.75),
            "center": (0.0, 0.0),
        }.get((target or "").lower())
        if target_xy is not None:
            tp = self._to_pixel(*target_xy)
            cv2.circle(canvas, tp, 18, (40, 40, 255), 3)
            cv2.circle(canvas, tp, 8, (0, 0, 255), -1)
            cv2.putText(
                canvas,
                f"LOOK {str(target).upper()}",
                (m, self.height - 64),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (40, 40, 255),
                2,
            )

        if direction and direction not in ("no_face", "no_eyes", "turn_to_camera"):
            cv2.putText(
                canvas,
                f"Looking: {direction.upper()}",
                (m, self.height - 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (80, 255, 160),
                2,
            )
        elif direction:
            cv2.putText(
                canvas,
                direction.replace("_", " ").upper(),
                (m, self.height - 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (80, 80, 220),
                2,
            )
        return canvas
