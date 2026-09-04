"""Call the live face check over HTTP exactly like the browser does.

Usage (from python_backend):
    .venv/Scripts/python.exe tools/http_face_check.py <image path> [base_url]
"""
import base64
import json
import sys
import urllib.request

path = sys.argv[1]
base = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8080"

with open(path, "rb") as f:
    payload = {"image": "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()}

req = urllib.request.Request(
    f"{base}/api/v1/live_face_check",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=180) as resp:
        print("HTTP", resp.status)
        print(json.dumps(json.loads(resp.read()), indent=2)[:1500])
except urllib.error.HTTPError as e:
    print("HTTP", e.code)
    print(e.read()[:800].decode("utf-8", errors="ignore"))
