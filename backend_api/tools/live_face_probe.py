"""Diagnostic: run the Step 4.1 live face check on an image file.

Usage (from python_backend):
    .venv/Scripts/python.exe tools/live_face_probe.py <image path>
"""
import base64
import json
import os
import sys

os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ocr.inproc import post_live_face_check


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    with open(sys.argv[1], "rb") as f:
        payload = {"image": "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()}
    code, data = post_live_face_check(payload)
    print("HTTP", code)
    print(json.dumps(data, indent=2)[:2000])


if __name__ == "__main__":
    main()
