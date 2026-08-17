"""
ZuDoc eye tracking demo

- Works no matter where the face is in the frame
- Tracks + plots ONLY when BOTH eyes face the camera
- Direction: top / bottom / left / right / center
- Live (x, y) graph for left & right pupils

Usage:
  cd "eye tracking"
  .\.venv\Scripts\activate
  python demo.py
"""

from __future__ import annotations

import argparse
import sys

import cv2
import numpy as np

from fgi_eye_tracker import EyeTracker
from fgi_eye_tracker.plot import EyeXYGraph


def main():
    parser = argparse.ArgumentParser(description="Eye tracking + (x,y) graph demo")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--weights", type=str, default=None)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()

    tracker = EyeTracker(
        weight_path=args.weights,
        device="cpu" if args.cpu else None,
    )
    graph = EyeXYGraph(width=520, height=520, history=80)

    cam = cv2.VideoCapture(args.camera)
    if not cam.isOpened():
        sys.exit("Could not open webcam. Check connection / permissions.")

    print("Face the camera and look straight for ~1s (auto-center). Esc = quit.")
    was_ready = False
    try:
        while True:
            ok, frame = cam.read()
            if not ok or frame is None:
                sys.exit("Lost webcam stream.")

            frame = cv2.flip(frame, 1)
            result = tracker.estimate(frame)
            cam_view = tracker.annotated_frame(frame, result)

            # When center calibration locks, clear old biased trail
            if result.calib_ready and not was_ready:
                graph.clear()
                was_ready = True
                print("Center calibrated — plot recentered.")

            # Plot points only when both eyes face the camera
            if result.both_eyes_facing:
                graph.push(result.left_xy, result.right_xy)
                plot_view = graph.render(direction=result.direction)
                if not result.calib_ready:
                    cv2.putText(
                        plot_view,
                        f"Calibrating center {int(result.calib_progress * 100)}% — look straight",
                        (36, 70),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (80, 200, 255),
                        2,
                    )
            else:
                plot_view = graph.render(direction=result.direction)
                cv2.putText(
                    plot_view,
                    "Waiting: both eyes must face camera",
                    (40, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (80, 80, 220),
                    2,
                )

            h = max(cam_view.shape[0], plot_view.shape[0])
            left = cv2.resize(cam_view, (int(cam_view.shape[1] * h / cam_view.shape[0]), h))
            right = cv2.resize(plot_view, (int(plot_view.shape[1] * h / plot_view.shape[0]), h))
            combo = np.hstack([left, right])
            cv2.imshow("ZuDoc Eye Tracking — direction + (x,y) graph", combo)

            if cv2.waitKey(1) & 0xFF == 27:
                break
    finally:
        tracker.close()
        cam.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
