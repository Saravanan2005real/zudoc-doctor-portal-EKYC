"""
Aadhaar Card OCR + eKYC portal (in-process on port 8080)
"""

import os
import sys

# Force UTF-8 encoding for stdout/stderr to prevent DeepFace emoji logging crashes on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from types import ModuleType
from importlib.machinery import ModuleSpec
from unittest.mock import MagicMock

# Dynamically intercept and mock all torch imports to bypass broken Windows PyTorch DLLs
class TorchMockFinder:
    def find_spec(self, fullname, path, target=None):
        if fullname == 'torch' or fullname.startswith('torch.'):
            return ModuleSpec(fullname, self, is_package=True)
        return None

    def create_module(self, spec):
        class MockModule(ModuleType):
            def __getattr__(self, name):
                if name == 'jit':
                    class JitMock:
                        class TracerWarning(Warning): pass
                    return JitMock
                m = MagicMock()
                m.__path__ = []
                return m
        mod = MockModule(spec.name)
        mod.__path__ = []
        return mod

    def exec_module(self, module):
        pass

sys.meta_path.insert(0, TorchMockFinder())
_TORCH_MOCK_FINDER = sys.meta_path[0]

# Disable oneDNN/MKLDNN to prevent the PIR implementation bug on CPU
os.environ['FLAGS_use_mkldnn'] = '0'
# Do NOT set TF_USE_LEGACY_KERAS=1 here — it breaks `import tensorflow.keras`
# which RetinaFace requires on TF 2.15 + standalone keras.
# Suppress TensorFlow C++ logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import warnings
warnings.filterwarnings("ignore")
import logging
import warnings
warnings.filterwarnings("ignore")
logging.getLogger('ppocr').setLevel(logging.ERROR)

# Suppress stdout/stderr during heavy imports to keep terminal clean
import sys, io
_old_stdout, _old_stderr = sys.stdout, sys.stderr
_sup_out, _sup_err = io.StringIO(), io.StringIO()
sys.stdout, sys.stderr = _sup_out, _sup_err
try:
    import json
    import re
    import uuid
    import cv2
    import numpy as np
    import base64
    from datetime import datetime
    from flask import Flask, request, jsonify, send_from_directory, render_template_string
    from flask_cors import CORS
    from PIL import Image
    import paddle
    from paddleocr import PaddleOCR

    # TensorFlow + RetinaFace BEFORE ultralytics/YOLO.
    # YOLO's torch mock can leave import state messy; load faces first.
    try:
        import tensorflow as _tf  # noqa: F401
        # Touch keras so tensorflow.keras submodule path resolves for RetinaFace.
        from tensorflow.keras.models import Model as _KerasModel  # noqa: F401
    except Exception as e:
        _sup_err.write(f"TensorFlow preload failed: {e}\n")

    try:
        from retinaface import RetinaFace
        _sup_err.write("RetinaFace loaded OK\n")
    except Exception as e:
        RetinaFace = None
        _sup_err.write(f"RetinaFace load failed: {e}\n")

    try:
        from deepface import DeepFace
        _sup_err.write("DeepFace loaded OK\n")
    except Exception as e:
        DeepFace = None
        _sup_err.write(f"DeepFace load failed: {e}\n")
finally:
    sys.stdout, sys.stderr = _old_stdout, _old_stderr
    captured = (_sup_err.getvalue() or "") + (_sup_out.getvalue() or "")
    for line in (captured or "").splitlines():
        if "RetinaFace" in line or "DeepFace" in line or "TensorFlow preload" in line:
            print(line, file=sys.stderr)
    fatal = any(k in captured.lower() for k in ("traceback", "error:", "exception"))
    if fatal and ("RetinaFace load failed" in captured or "DeepFace load failed" in captured):
        print(captured[-2000:], file=sys.stderr)


def _release_torch_mock():
    """Drop the Paddle-only torch mock so EyeTracker can import real PyTorch."""
    try:
        sys.meta_path.remove(_TORCH_MOCK_FINDER)
    except ValueError:
        pass
    for finder in list(sys.meta_path):
        if finder.__class__.__name__ == "TorchMockFinder":
            try:
                sys.meta_path.remove(finder)
            except ValueError:
                pass
    for key in list(sys.modules):
        if key == "torch" or key.startswith("torch."):
            sys.modules.pop(key, None)


_release_torch_mock()

# Suppress paddlex logger
import logging
paddlex_logger = logging.getLogger('paddlex')
paddlex_logger.setLevel(logging.ERROR)
for handler in paddlex_logger.handlers:
    paddlex_logger.removeHandler(handler)

app = Flask(__name__)
CORS(app)


# Ensure upload directory exists — use an absolute path so the folder is always
# python_backend/ocr_uploads/ regardless of the working directory at launch time.
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ocr_uploads')
UPLOAD_FOLDER = os.path.abspath(UPLOAD_FOLDER)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def _save_jpg(path: str, img) -> bool:
    try:
        ok = cv2.imwrite(path, img)
        return bool(ok) and os.path.exists(path) and os.path.getsize(path) > 0
    except Exception:
        return False


def _json_safe(obj):
    """Convert numpy / nested RetinaFace values into plain JSON types."""
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        return float(obj)
    # numpy scalars (float32, int64, bool_, etc.)
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return _json_safe(obj.tolist())
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    # Fallback: stringify unknown objects rather than crash jsonify
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aadhaar / PAN OCR Processing Portal</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0d0f14;
            --card-bg: rgba(22, 28, 45, 0.4);
            --border-color: rgba(255, 255, 255, 0.08);
            --accent-color: #4f46e5;
            --text-color: #e2e8f0;
            --text-muted: #94a3b8;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Outfit', sans-serif;
            margin: 0;
            padding: 40px 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background-image: radial-gradient(circle at 10% 20%, rgba(79, 70, 229, 0.15) 0%, transparent 40%),
                              radial-gradient(circle at 90% 80%, rgba(99, 102, 241, 0.1) 0%, transparent 45%);
        }

        .container {
            max-width: 950px;
            width: 100%;
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }

        h1 {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        p.subtitle {
            color: var(--text-muted);
            margin-top: 0;
            margin-bottom: 40px;
            font-size: 1.1rem;
        }

        .grid {
            display: grid;
            grid-template-columns: 1fr 1.2fr;
            gap: 40px;
        }

        .upload-section {
            border: 2px dashed rgba(255, 255, 255, 0.15);
            border-radius: 16px;
            padding: 30px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
        }

        .upload-section:hover {
            border-color: var(--accent-color);
            background: rgba(79, 70, 229, 0.05);
        }

        .upload-section input[type="file"] {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            opacity: 0;
            cursor: pointer;
        }

        .upload-icon {
            font-size: 3rem;
            margin-bottom: 15px;
            color: #818cf8;
        }

        .btn {
            background: var(--accent-color);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
            margin-top: 20px;
            width: 100%;
        }

        .btn:hover {
            opacity: 0.9;
        }

        .preview-box {
            margin-top: 20px;
            display: none;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }

        .preview-box img {
            width: 100%;
            display: block;
        }

        .result-section {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .card {
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
        }

        .card-title {
            font-weight: 600;
            color: #a5b4fc;
            margin-bottom: 15px;
            font-size: 1.1rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .field {
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding: 10px 0;
        }

        .field:last-child {
            border-bottom: none;
        }

        .field-name {
            color: var(--text-muted);
        }

        .field-val {
            font-weight: 600;
        }

        .badge {
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
        }

        .badge-success { background: rgba(16, 185, 129, 0.2); color: #34d399; }
        .badge-error { background: rgba(239, 68, 68, 0.2); color: #f87171; }

        pre {
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            border: 1px solid var(--border-color);
            font-size: 0.9rem;
            margin: 0;
            color: #a7f3d0;
        }

        .loader {
            display: none;
            text-align: center;
            padding: 20px;
            color: var(--text-muted);
        }

        .loader::after {
            content: "";
            display: inline-block;
            width: 30px;
            height: 30px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: var(--accent-color);
            animation: spin 1s ease-in-out infinite;
            margin-left: 10px;
            vertical-align: middle;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Aadhaar / PAN OCR Portal</h1>
        <p class="subtitle" style="margin-bottom: 10px;">Step 1: Upload &amp; Verify Aadhaar or PAN Document</p>
        <div style="display:flex; gap:10px; margin-bottom: 30px;">
            <div style="flex:1; height:6px; border-radius:3px; background: var(--accent-color);"></div>
            <div style="flex:1; height:6px; border-radius:3px; background: rgba(255,255,255,0.1);"></div>
        </div>
        
        <div class="grid">
            <div>
                <form id="upload-form">
                    <div class="upload-section">
                        <div class="upload-icon">📁</div>
                        <h3>Choose or drag image here</h3>
                        <p style="color: var(--text-muted); font-size: 0.9rem;">Supports Aadhaar or PAN Card (JPG, PNG) — document type is auto-detected</p>
                        <input type="file" id="file-input" name="file" accept="image/*" required>
                    </div>
                    <button type="submit" class="btn">Process Image</button>
                </form>

                <div class="preview-box" id="preview-box">
                    <h4 style="margin: 15px; color: #a5b4fc;">Original Upload:</h4>
                    <img id="image-preview" src="">
                </div>
            </div>

            <div class="result-section">
                <div class="loader" id="loader">Running Pipeline...</div>
                
                <div id="results" style="display: none;">
                    <div class="card">
                        <div class="card-title">Parsed Output &nbsp; <span class="badge" id="doc-type-badge">-</span></div>
                        <div class="field">
                            <span class="field-name">Name</span>
                            <span class="field-val" id="res-name">-</span>
                        </div>
                        <div class="field">
                            <span class="field-name">Date of Birth</span>
                            <span class="field-val" id="res-dob">-</span>
                        </div>
                        <div class="field" id="gender-row">
                            <span class="field-name">Gender</span>
                            <span class="field-val" id="res-gender">-</span>
                        </div>
                        <div class="field" id="father-row" style="display: none;">
                            <span class="field-name">Father's Name</span>
                            <span class="field-val" id="res-father">-</span>
                        </div>
                        <div class="field">
                            <span class="field-name" id="id-num-label">Aadhaar Number</span>
                            <span class="field-val" id="res-idnum">-</span>
                        </div>
                        <div class="field">
                            <span class="field-name" id="check-label">Verhoeff Check</span>
                            <span id="res-valid">-</span>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-title">Quality & Pipeline</div>
                        <div class="field">
                            <span class="field-name">Resolution</span>
                            <span class="field-val" id="res-dim">-</span>
                        </div>
                        <div class="field">
                            <span class="field-name">Blur Score</span>
                            <span class="field-val" id="res-blur">-</span>
                        </div>
                        <div class="field">
                            <span class="field-name">Lighting</span>
                            <span class="field-val" id="res-light">-</span>
                        </div>
                        <div class="field">
                            <span class="field-name">Face Detected</span>
                            <span class="field-val" id="res-face">-</span>
                        </div>
                        <div class="field">
                            <span class="field-name">Half Card Check</span>
                            <span class="field-val" id="res-half">-</span>
                        </div>
                        <div class="field">
                            <span class="field-name">Warp Corrected</span>
                            <span class="field-val" id="res-warp">-</span>
                        </div>
                        <div class="field">
                            <span class="field-name">OCR Confidence</span>
                            <span class="field-val" id="res-conf">-</span>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-title">Raw Text Lines</div>
                        <pre id="raw-text"></pre>
                    </div>

                    <div class="card" id="processed-card" style="display: none;">
                        <div class="card-title">Corrected/Enhanced Image</div>
                        <img id="processed-image" src="" style="width:100%; border-radius:8px; border: 1px solid var(--border-color);">
                    </div>

                    <div class="card" id="face-card" style="display: none;">
                        <div class="card-title">Extracted Face (112x112)</div>
                        <div style="text-align: center; padding: 10px;">
                            <img id="extracted-face" src="" style="width:112px; height:112px; border-radius:8px; border: 2px solid var(--accent-color); object-fit: cover;">
                        </div>
                    </div>

                    <button id="proceed-btn" class="btn" style="display: none; background: #10b981;">Step 1 Passed &check; &nbsp; Proceed to Step 2: Live Verification &rarr;</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let step1FaceFilename = "";
        const fileInput = document.getElementById('file-input');
        const imgPreview = document.getElementById('image-preview');
        const previewBox = document.getElementById('preview-box');
        const uploadForm = document.getElementById('upload-form');
        const loader = document.getElementById('loader');
        const results = document.getElementById('results');

        fileInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    imgPreview.src = e.target.result;
                    previewBox.style.display = 'block';
                }
                reader.readAsDataURL(file);
            }
        });

        uploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            loader.style.display = 'block';
            results.style.display = 'none';

            try {
                const resp = await fetch('/api/v1/ocr', {
                    method: 'POST',
                    body: formData
                });
                const data = await resp.json();

                if (data.status === 'success') {
                    // Populate fields
                    const docType = data.parsed_fields.document_type || 'UNKNOWN';
                    const docBadge = document.getElementById('doc-type-badge');
                    docBadge.innerText = docType === 'PAN' ? 'PAN CARD' : (docType === 'AADHAAR' ? 'AADHAAR CARD' : 'UNKNOWN');
                    docBadge.className = 'badge ' + (docType === 'UNKNOWN' ? 'badge-error' : 'badge-success');

                    document.getElementById('res-name').innerText = data.parsed_fields.name || 'Not Found';
                    document.getElementById('res-dob').innerText = data.parsed_fields.dob || 'Not Found';

                    let isValid = false;
                    let idNumber = '';
                    if (docType === 'PAN') {
                        document.getElementById('gender-row').style.display = 'none';
                        document.getElementById('father-row').style.display = 'flex';
                        document.getElementById('res-father').innerText = data.parsed_fields.father_name || 'Not Found';
                        document.getElementById('id-num-label').innerText = 'PAN Number';
                        document.getElementById('check-label').innerText = 'Format Check';
                        idNumber = data.parsed_fields.pan_number;
                        isValid = data.parsed_fields.pan_number_validated;
                    } else {
                        document.getElementById('gender-row').style.display = 'flex';
                        document.getElementById('father-row').style.display = 'none';
                        document.getElementById('res-gender').innerText = data.parsed_fields.gender || 'Not Found';
                        document.getElementById('id-num-label').innerText = 'Aadhaar Number';
                        document.getElementById('check-label').innerText = 'Verhoeff Check';
                        idNumber = data.parsed_fields.aadhaar_number;
                        isValid = data.parsed_fields.aadhaar_number_validated;
                    }
                    document.getElementById('res-idnum').innerText = idNumber || 'Not Found';

                    const validBadge = document.getElementById('res-valid');
                    validBadge.className = isValid ? 'badge badge-success' : 'badge badge-error';
                    validBadge.innerText = isValid ? 'VALID' : 'INVALID';

                    document.getElementById('res-dim').innerText = data.quality_check.dimensions;
                    document.getElementById('res-blur').innerText = `${data.quality_check.blur_variance} (${data.quality_check.blur_status})`;
                    document.getElementById('res-light').innerText = data.quality_check.brightness_status;
                    
                    const faceStatus = data.quality_check.face_visible ? 
                        (data.quality_check.face_not_cropped && data.quality_check.face_not_too_small ? 'OK' : 'CROPPED/SMALL') : 'NOT FOUND';
                    document.getElementById('res-face').innerText = faceStatus;
                    document.getElementById('res-half').innerText = data.quality_check.is_half_card ? 'YES (Rejected)' : 'NO (OK)';

                    document.getElementById('res-warp').innerText = data.perspective_corrected ? 'Yes' : 'No';
                    document.getElementById('res-conf').innerText = `${data.ocr_confidence}%`;

                    document.getElementById('raw-text').innerText = data.raw_text.join('\\n') || 'Empty';

                    if (data.processed_image_url) {
                        const procImg = document.getElementById('processed-image');
                        procImg.src = data.processed_image_url;
                        document.getElementById('processed-card').style.display = 'block';
                    } else {
                        document.getElementById('processed-card').style.display = 'none';
                    }

                    if (data.face_image_url) {
                        step1FaceFilename = data.face_image_url.split('/').pop();
                        const faceImg = document.getElementById('extracted-face');
                        faceImg.src = data.face_image_url;
                        document.getElementById('face-card').style.display = 'block';
                    } else {
                        document.getElementById('face-card').style.display = 'none';
                    }

                    results.style.display = 'block';
                    
                    // Always persist the uploaded face crop for live cross-verify.
                    if (step1FaceFilename) {
                        localStorage.setItem('step1FaceFilename', step1FaceFilename);
                    }
                    // Show proceed button if validation passes
                    if (isValid) {
                        document.getElementById('proceed-btn').style.display = 'block';
                    } else {
                        document.getElementById('proceed-btn').style.display = 'none';
                    }
                } else {
                    alert('OCR Error: ' + (data.error || 'Unknown error'));
                }
            } catch (err) {
                alert('Connection Error: ' + err.message);
            } finally {
                loader.style.display = 'none';
            }
        });

        // --- STEP 2 LOGIC ---
        document.getElementById('proceed-btn').addEventListener('click', () => {
            window.location.href = '/live';
        });
    </script>
</body>
</html>
"""

STEP2_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live Verification - Step 2</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0d0f14;
            --card-bg: rgba(22, 28, 45, 0.4);
            --border-color: rgba(255, 255, 255, 0.08);
            --accent-color: #4f46e5;
            --text-color: #e2e8f0;
            --text-muted: #94a3b8;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Outfit', sans-serif;
            margin: 0;
            padding: 40px 20px;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            min-height: 100vh;
            background-image: radial-gradient(circle at 10% 20%, rgba(79, 70, 229, 0.15) 0%, transparent 40%),
                              radial-gradient(circle at 90% 80%, rgba(99, 102, 241, 0.1) 0%, transparent 45%);
        }

        .container {
            max-width: 950px;
            width: 100%;
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }

        h1 {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        p.subtitle {
            color: var(--text-muted);
            margin-top: 0;
            margin-bottom: 10px;
            font-size: 1.1rem;
        }

        .grid {
            display: grid;
            grid-template-columns: 1fr 1.2fr;
            gap: 40px;
        }

        .video-container {
            position: relative;
            width: 100%;
            border-radius: 16px;
            overflow: hidden;
            border: 2px solid var(--border-color);
            background: #000;
        }

        video {
            width: 100%;
            display: block;
            transform: scaleX(-1); /* Mirror effect */
        }

        .btn {
            background: var(--accent-color);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
            margin-top: 20px;
            width: 100%;
            text-align: center;
            text-decoration: none;
            display: block;
            box-sizing: border-box;
        }

        .btn:hover {
            opacity: 0.9;
        }

        .result-section {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .card {
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
        }

        .card-title {
            font-weight: 600;
            color: #a5b4fc;
            margin-bottom: 15px;
            font-size: 1.1rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .field {
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding: 10px 0;
        }

        .field:last-child {
            border-bottom: none;
        }

        .field-name {
            color: var(--text-muted);
        }

        .field-val {
            font-weight: 600;
        }

        .badge {
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
        }

        .badge-success { background: rgba(16, 185, 129, 0.2); color: #34d399; }
        .badge-error { background: rgba(239, 68, 68, 0.2); color: #f87171; }

        .loader {
            display: none;
            text-align: center;
            padding: 20px;
            color: var(--text-muted);
        }

        .loader::after {
            content: "";
            display: inline-block;
            width: 30px;
            height: 30px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: var(--accent-color);
            animation: spin 1s ease-in-out infinite;
            margin-left: 10px;
            vertical-align: middle;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .warning-box {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #f87171;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h1>Live Verification</h1>
            <a href="/" class="btn" style="width: auto; margin-top: 0;">&larr; Back to Step 1</a>
        </div>
        <p class="subtitle" style="margin-bottom: 10px;">Step 2: Live Face &amp; Document Match</p>
        <div style="display:flex; gap:10px; margin-bottom: 30px;">
            <div style="flex:1; height:6px; border-radius:3px; background: var(--accent-color);"></div>
            <div style="flex:1; height:6px; border-radius:3px; background: var(--accent-color);"></div>
        </div>
        <p class="subtitle">Hold your Aadhaar or PAN card next to your face and click Capture</p>
        
        <div class="grid">
            <div>
                <div class="video-container">
                    <video id="webcam" autoplay playsinline></video>
                </div>
                <button id="capture-btn" class="btn">Capture &amp; Verify</button>
                <canvas id="canvas" style="display: none;"></canvas>
            </div>
            
            <div class="result-section">
                <div class="loader" id="loader">Processing Frame...</div>
                
                <div id="results" style="display: none;">
                    <div class="card" id="face-card">
                        <div class="card-title">Live Face Extracted</div>
                        <div style="text-align: center; padding: 10px;">
                            <img id="extracted-face" src="" style="width:112px; height:112px; border-radius:8px; border: 2px solid var(--accent-color); object-fit: cover;">
                        </div>
                    </div>

                    <div class="card" id="live-doc-card" style="display: none;">
                        <div class="card-title">Analyzed Document</div>
                        <img id="live-doc-image" src="" style="width:100%; border-radius:8px; border: 1px solid var(--border-color);">
                    </div>

                    <div class="card">
                        <div class="card-title">Extracted ID Details &nbsp; <span class="badge" id="doc-type-badge">-</span></div>
                        <div class="field">
                            <span class="field-name" id="id-num-label">ID Number</span>
                            <span class="field-val" id="res-idnum">-</span>
                        </div>
                        <div class="field">
                            <span class="field-name" id="check-label">Format Check</span>
                            <span id="res-valid">-</span>
                        </div>
                        <div class="field">
                            <span class="field-name">Face Match (Step 1 vs Live)</span>
                            <span id="res-face-match">-</span>
                        </div>
                    </div>

                    <button id="finish-btn" class="btn" style="display: none; background: #10b981;">Verification Complete &check;</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const video = document.getElementById('webcam');
        const canvas = document.getElementById('canvas');
        const captureBtn = document.getElementById('capture-btn');
        const loader = document.getElementById('loader');
        const results = document.getElementById('results');
        const finishBtn = document.getElementById('finish-btn');

        // Request webcam access
        navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } } })
            .then(stream => { 
                video.srcObject = stream; 
            })
            .catch(err => { 
                alert("Webcam access denied or unavailable: " + err); 
            });

        captureBtn.addEventListener('click', async () => {
            // Draw video frame to canvas
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            
            // Draw normally without mirroring so OCR can read the text correctly
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            // Convert to base64
            const base64Image = canvas.toDataURL('image/jpeg', 0.9);
            
            loader.style.display = 'block';
            results.style.display = 'none';
            finishBtn.style.display = 'none';
            
            try {
                const resp = await fetch('/api/v1/live_verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        image: base64Image,
                        step1_face: localStorage.getItem('step1FaceFilename') || ''
                    })
                });
                const data = await resp.json();
                
                if (data.status === 'success') {
                    const docType = data.parsed_fields.document_type || 'UNKNOWN';
                    const docBadge = document.getElementById('doc-type-badge');
                    docBadge.innerText = docType === 'PAN' ? 'PAN CARD' : (docType === 'AADHAAR' ? 'AADHAAR CARD' : 'UNKNOWN');
                    docBadge.className = 'badge ' + (docType === 'UNKNOWN' ? 'badge-error' : 'badge-success');

                    let isValid = false;
                    let idNumber = '';
                    if (docType === 'PAN') {
                        document.getElementById('id-num-label').innerText = 'PAN Number';
                        document.getElementById('check-label').innerText = 'Format Check';
                        idNumber = data.parsed_fields.pan_number;
                        isValid = data.parsed_fields.pan_number_validated;
                    } else {
                        document.getElementById('id-num-label').innerText = 'Aadhaar Number';
                        document.getElementById('check-label').innerText = 'Verhoeff Check';
                        idNumber = data.parsed_fields.aadhaar_number;
                        isValid = data.parsed_fields.aadhaar_number_validated;
                    }
                    document.getElementById('res-idnum').innerText = idNumber || 'Not Found';

                    const validBadge = document.getElementById('res-valid');
                    validBadge.className = isValid ? 'badge badge-success' : 'badge badge-error';
                    validBadge.innerText = isValid ? 'VALID' : 'INVALID';
                    
                    const faceMatchBadge = document.getElementById('res-face-match');
                    if (data.face_match === true) {
                        faceMatchBadge.className = 'badge badge-success';
                        faceMatchBadge.innerText = 'MATCHED';
                    } else if (data.face_match === false) {
                        faceMatchBadge.className = 'badge badge-error';
                        faceMatchBadge.innerText = 'NOT MATCHED';
                    } else {
                        faceMatchBadge.className = 'badge';
                        faceMatchBadge.innerText = 'N/A (no uploaded face)';
                    }
                    
                    if (data.face_image_url) {
                        document.getElementById('extracted-face').src = data.face_image_url;
                        document.getElementById('face-card').style.display = 'block';
                    } else {
                        document.getElementById('face-card').style.display = 'none';
                    }
                    
                    if (data.processed_image_url) {
                        document.getElementById('live-doc-image').src = data.processed_image_url;
                        document.getElementById('live-doc-card').style.display = 'block';
                    } else {
                        document.getElementById('live-doc-card').style.display = 'none';
                    }
                    
                    results.style.display = 'block';

                    if (isValid) {
                        finishBtn.style.display = 'block';
                    }
                } else {
                    alert('Verification Error: ' + (data.error || 'Unknown error'));
                }
            } catch (err) {
                alert('Connection Error: ' + err.message);
            } finally {
                loader.style.display = 'none';
            }
        });

        finishBtn.addEventListener('click', () => {
            alert('eKYC Verification completed successfully!');
        });
    </script>
</body>
</html>
"""

# Initialize PaddleOCR (downloads models on first run)
# lang="en" is standard for Aadhaar cards as name, DOB, number are printed in English.
ocr = PaddleOCR(use_textline_orientation=True, lang="en", enable_mkldnn=False)



# Verhoeff Algorithm for Aadhaar Validation
VERHOEFF_TABLE_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

VERHOEFF_TABLE_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

VERHOEFF_TABLE_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

def validate_verhoeff(num_str: str) -> bool:
    try:
        numbers = [int(x) for x in num_str]
        numbers.reverse()
        c = 0
        for i, val in enumerate(numbers):
            c = VERHOEFF_TABLE_D[c][VERHOEFF_TABLE_P[i % 8][val]]
        return c == 0
    except ValueError:
        return False

# Image Quality Check
def check_image_quality(img_np):
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    img_area = h * w
    
    # 1. Size and Aspect Ratio (Half card check)
    size_ok = (h >= 400 and w >= 400)
    aspect_ratio = max(w, h) / min(w, h)
    # Aadhaar card is ~1.58. If it's < 1.2 or > 2.2, it might be a half card or badly cropped
    is_half_card = aspect_ratio < 1.2 or aspect_ratio > 2.2
    
    # 2. Blurry check (Laplacian variance)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    blur_status = "OK" if laplacian_var > 100.0 else "BLURRY"
    
    # 3. Brightness/Contrast (Overexposed / Too Dark)
    avg_brightness = np.mean(gray)
    brightness_status = "OK"
    if avg_brightness < 40:
        brightness_status = "TOO_DARK"
    elif avg_brightness > 220:
        brightness_status = "OVEREXPOSED"

    # 4. Face Detection (Visible, Not Cropped, Not Too Small)
    face_visible = False
    face_not_cropped = True
    face_not_too_small = True
    faces = []
    if hasattr(cv2, "CascadeClassifier"):
        haar_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "eye_tracking",
            "fgi_eye_tracker",
            "data",
            "haarcascade_frontalface_default.xml",
        )
        haar_path = os.path.abspath(haar_path)
        if not os.path.isfile(haar_path):
            haar_dir = getattr(getattr(cv2, "data", None), "haarcascades", "") or ""
            haar_path = os.path.join(haar_dir, "haarcascade_frontalface_default.xml")
        try:
            face_cascade = cv2.CascadeClassifier(haar_path)
            if not face_cascade.empty():
                faces = face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                )
        except Exception:
            faces = []

    if len(faces) > 0:
        face_visible = True
        # Get the largest face
        fx, fy, fw, fh = max(faces, key=lambda rect: rect[2] * rect[3])
        face_area = fw * fh

        # Check if too small (e.g., face is less than 0.5% of the image)
        if (face_area / img_area) < 0.005:
            face_not_too_small = False

        # Check if cropped (too close to the edge)
        margin = int(min(w, h) * 0.02) # 2% margin
        if fx < margin or fy < margin or (fx + fw) > (w - margin) or (fy + fh) > (h - margin):
            face_not_cropped = False

    # 5. Compression Artifacts
    # We use blur_variance and resolution as a proxy for heavy compression/bad screenshots
    # If it's very blurry and small, it's likely a bad screenshot.
    
    passed = (
        size_ok and
        not is_half_card and
        blur_status == "OK" and
        brightness_status == "OK" and
        face_visible and
        face_not_cropped and
        face_not_too_small
    )
        
    return {
        "dimensions": f"{w}x{h}",
        "resolution_ok": size_ok,
        "is_half_card": is_half_card,
        "blur_variance": round(laplacian_var, 2),
        "blur_status": blur_status,
        "average_brightness": round(avg_brightness, 2),
        "brightness_status": brightness_status,
        "face_visible": face_visible,
        "face_not_cropped": face_not_cropped,
        "face_not_too_small": face_not_too_small,
        "passed": passed
    }

# Document Detection & Perspective Correction (YOLO + Contour Fallback)
def detect_and_warp_document(img_np):
    h, w, _ = img_np.shape
    
    # YOLO Document Detection (if YOLO is available and trained)
    # We use a bounding box to crop the region of interest first
    if yolo_model is not None:
        try:
            results = yolo_model(img_np, verbose=False)
            if len(results) > 0 and len(results[0].boxes) > 0:
                # Get the highest confidence box
                box = results[0].boxes[0].xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = map(int, box)
                
                # Add some padding
                pad = 20
                x1 = max(0, x1 - pad)
                y1 = max(0, y1 - pad)
                x2 = min(w, x2 + pad)
                y2 = min(h, y2 + pad)
                
                img_np = img_np[y1:y2, x1:x2]
                h, w, _ = img_np.shape
        except Exception as e:
            print(f"YOLO detection failed, falling back to full image: {e}")

    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)
    
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    
    doc_contour = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            doc_contour = approx
            break
            
    if doc_contour is not None:
        # Perspective Correction (Warp)
        pts = doc_contour.reshape(4, 2)
        rect = np.zeros((4, 2), dtype="float32")
        
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        (tl, tr, br, bl) = rect
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img_np, M, (maxWidth, maxHeight))
        return warped, True
    
    return img_np, False

def _apply_clahe(img_np, clip_limit=2.0):
    """Mild LAB CLAHE — strong enough for shadows, gentle enough for PaddleOCR."""
    lab = cv2.cvtColor(img_np, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)


def _maybe_upscale_for_ocr(img_np):
    """Upscale only small/soft images. Aggressive FSRCNN on sharp scans hurts Latin OCR."""
    h, w = img_np.shape[:2]
    min_side = min(h, w)
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    blur_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    # Already high-res and sharp — leave geometry alone
    if min_side >= 900 and blur_var >= 80:
        return img_np

    need_sr = min_side < 700 or blur_var < 60
    if not need_sr:
        if min_side < 1000:
            scale = 1.5
            return cv2.resize(
                img_np,
                (int(w * scale), int(h * scale)),
                interpolation=cv2.INTER_CUBIC,
            )
        return img_np

    try:
        sr = cv2.dnn_superres.DnnSuperResImpl_create()
        model_path = os.path.join(os.path.dirname(__file__), "FSRCNN_x2.pb")
        if os.path.exists(model_path):
            sr.readModel(model_path)
            sr.setModel("fsrcnn", 2)
            return sr.upsample(img_np)
    except Exception as e:
        print(f"Super-resolution failed, falling back to cubic resize: {e}")

    return cv2.resize(img_np, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)


def enhance_image_for_ocr(img_np):
    """
    OCR-safe enhancement.

    Post-integration Level-2 pipeline (always FSRCNN + heavy denoise + unsharp)
    corrupted Latin text on clear Aadhaar scans (e.g. 'Dinesh S' → 'UDSIL IFTHIBLD').
    Prefer mild CLAHE; only upscale/denoise when the source is small or soft.
    """
    img_np = _maybe_upscale_for_ocr(img_np)
    enhanced = _apply_clahe(img_np, clip_limit=2.0)

    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    blur_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    # Light denoise only for noisy/soft sources — skip on sharp cards
    if blur_var < 120:
        enhanced = cv2.fastNlMeansDenoisingColored(enhanced, None, 6, 6, 7, 21)

    return enhanced


def prepare_ocr_candidates(img_np):
    """
    Build 1–2 images for PaddleOCR and keep the best read.
    Candidate A: mild enhance (primary).
    Candidate B: raw warped crop when primary text looks weak.
    """
    mild = enhance_image_for_ocr(img_np)
    return [("mild", mild), ("raw", img_np.copy())]

# Face Extraction & Alignment using RetinaFace + fallback
def _face_detection_candidates(primary_bgr, original_bgr=None):
    """
    Build candidate images for face extraction, from most likely to least likely.
    """
    candidates = []
    if primary_bgr is not None:
        candidates.append(("warped", primary_bgr))

        # Mild contrast enhancement can help on dim camera frames.
        try:
            candidates.append(("warped_clahe", _apply_clahe(primary_bgr, clip_limit=2.0)))
        except Exception:
            pass

    if original_bgr is not None:
        candidates.append(("original", original_bgr))
        try:
            candidates.append(("original_clahe", _apply_clahe(original_bgr, clip_limit=2.0)))
        except Exception:
            pass
    return candidates


def _square_face_crop_coords(x1, y1, x2, y2, iw, ih, mode="doc"):
    """
    mode=doc: generous crop for uploaded ID scans.
    mode=tight: live webcam — stay on the face so a held ID card is not included.
    """
    bw = max(1, int(x2 - x1))
    bh = max(1, int(y2 - y1))
    if mode == "tight":
        left_pad = int(bw * 0.10)
        right_pad = int(bw * 0.10)
        top_pad = int(bh * 0.16)
        bottom_pad = int(bh * 0.12)
        size_mult = 1.12
    else:
        left_pad = int(bw * 0.20)
        right_pad = int(bw * 0.20)
        top_pad = int(bh * 0.40)
        bottom_pad = int(bh * 0.30)
        size_mult = 1.5
    ex1 = int(x1) - left_pad
    ey1 = int(y1) - top_pad
    ex2 = int(x2) + right_pad
    ey2 = int(y2) + bottom_pad
    ew = max(1, ex2 - ex1)
    eh = max(1, ey2 - ey1)
    size = int(max(max(bw, bh) * size_mult, ew, eh))
    cx = (int(x1) + int(x2)) / 2.0
    cy = (int(y1) + int(y2)) / 2.0
    half = size / 2.0
    sx1 = int(round(cx - half))
    sy1 = int(round(cy - half))
    sx2 = sx1 + size
    sy2 = sy1 + size
    if sx1 < 0:
        sx2 -= sx1
        sx1 = 0
    if sy1 < 0:
        sy2 -= sy1
        sy1 = 0
    if sx2 > iw:
        sx1 -= (sx2 - iw)
        sx2 = iw
    if sy2 > ih:
        sy1 -= (sy2 - ih)
        sy2 = ih
    sx1 = max(0, sx1)
    sy1 = max(0, sy1)
    sx2 = min(iw, sx2)
    sy2 = min(ih, sy2)
    if sx2 <= sx1 or sy2 <= sy1:
        return None
    return sx1, sy1, sx2, sy2


def _save_debug_crop(crop):
    try:
        path = os.path.join(app.config.get("UPLOAD_FOLDER") or UPLOAD_FOLDER, "debug_crop.jpg")
        cv2.imwrite(path, crop)
    except Exception:
        pass


def _opencv_face_fallback(img_bgr):
    """
    Last-resort fallback if RetinaFace misses.
    """
    try:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        face_cascade = cv2.CascadeClassifier(cascade_path)
        if face_cascade.empty():
            return None
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(24, 24))
        if faces is None or len(faces) == 0:
            return None
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        ih, iw = img_bgr.shape[:2]
        box = _square_face_crop_coords(x, y, x + w, y + h, iw, ih, mode="tight")
        if box is None:
            return None
        x1, y1, x2, y2 = box
        crop = img_bgr[y1:y2, x1:x2]
        if crop.size == 0:
            return None
        _save_debug_crop(crop)
        return cv2.resize(crop, (112, 112), interpolation=cv2.INTER_AREA), {
            "source": "opencv_haar",
            "confidence": None,
            "bbox": [int(x1), int(y1), int(x2), int(y2)],
            "landmarks": None,
            "aligned": False,
        }
    except Exception:
        return None


def _to_3point(landmarks):
    if not isinstance(landmarks, dict):
        return None
    le = landmarks.get("left_eye")
    re = landmarks.get("right_eye")
    no = landmarks.get("nose")
    if not le or not re or not no:
        return None
    try:
        return np.float32([[float(le[0]), float(le[1])], [float(re[0]), float(re[1])], [float(no[0]), float(no[1])]])
    except Exception:
        return None


def _align_and_crop_from_detection(img_bgr, det, crop_mode="doc"):
    """
    Original image → RetinaFace bbox → expand → square crop
    → eye alignment on that crop → final square → 112×112.
    Never resize before padding/crop.
    """
    facial_area = det.get("facial_area") or det.get("bbox")
    landmarks = det.get("landmarks")
    if not facial_area or len(facial_area) != 4:
        return None, None

    x1, y1, x2, y2 = [int(v) for v in facial_area]
    ih, iw = img_bgr.shape[:2]
    if x2 <= x1 or y2 <= y1:
        return None, None

    box = _square_face_crop_coords(x1, y1, x2, y2, iw, ih, mode=crop_mode)
    if box is None:
        return None, None
    sx1, sy1, sx2, sy2 = box
    crop = img_bgr[sy1:sy2, sx1:sx2]
    if crop.size == 0:
        return None, None

    _save_debug_crop(crop)

    aligned = False
    three = _to_3point(landmarks)
    if three is not None:
        pts = three.copy()
        pts[:, 0] -= float(sx1)
        pts[:, 1] -= float(sy1)
        # Ignore RetinaFace L/R labels — swapped eyes produced a ~180° rotation.
        if pts[0][0] > pts[1][0]:
            pts[[0, 1]] = pts[[1, 0]]
        le_x, le_y = float(pts[0][0]), float(pts[0][1])
        re_x, re_y = float(pts[1][0]), float(pts[1][1])
        nose_x, nose_y = float(pts[2][0]), float(pts[2][1])
        eyes_y = (le_y + re_y) / 2.0
        # Image y grows downward; eyes must sit above the nose. Otherwise the
        # crop (or the whole frame) is inverted.
        if nose_y < eyes_y:
            crop = cv2.rotate(crop, cv2.ROTATE_180)
            ch, cw = crop.shape[:2]
            pts[:, 0] = cw - 1 - pts[:, 0]
            pts[:, 1] = ch - 1 - pts[:, 1]
            if pts[0][0] > pts[1][0]:
                pts[[0, 1]] = pts[[1, 0]]
            le_x, le_y = float(pts[0][0]), float(pts[0][1])
            re_x, re_y = float(pts[1][0]), float(pts[1][1])
            aligned = True
        dx = re_x - le_x
        dy = re_y - le_y
        angle = float(np.degrees(np.arctan2(dy, dx))) if (abs(dx) > 1e-3 or abs(dy) > 1e-3) else 0.0
        if 0.8 < abs(angle) <= 45.0:
            ch, cw = crop.shape[:2]
            M = cv2.getRotationMatrix2D((cw / 2.0, ch / 2.0), angle, 1.0)
            crop = cv2.warpAffine(
                crop, M, (cw, ch),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )
            aligned = True

    # Final square crop from the (possibly rotated) expanded region.
    ch, cw = crop.shape[:2]
    side = min(ch, cw)
    y0 = (ch - side) // 2
    x0 = (cw - side) // 2
    final = crop[y0:y0 + side, x0:x0 + side]
    if final.size == 0:
        final = crop

    return cv2.resize(final, (112, 112), interpolation=cv2.INTER_AREA), aligned


def _detect_faces_on_image(img_bgr, source_label="frame", crop_mode="doc"):
    """
    Run RetinaFace (then OpenCV fallback) and return every face found.
    Each item: {"face": 112x112 BGR, "area": int, "meta": dict}
    Sorted largest-area first.
    """
    found = []
    if img_bgr is None or getattr(img_bgr, "size", 0) == 0:
        return found

    if RetinaFace is not None:
        try:
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            detections = RetinaFace.detect_faces(rgb)
            if detections and isinstance(detections, dict):
                for _, det in detections.items():
                    if not isinstance(det, dict):
                        continue
                    area_box = det.get("facial_area") or [0, 0, 0, 0]
                    if len(area_box) != 4:
                        continue
                    x1, y1, x2, y2 = [int(v) for v in area_box]
                    area = max(0, x2 - x1) * max(0, y2 - y1)
                    if area <= 0:
                        continue
                    face112, aligned = _align_and_crop_from_detection(
                        img_bgr, det, crop_mode=crop_mode
                    )
                    if face112 is None:
                        continue
                    found.append({
                        "face": face112,
                        "area": area,
                        "meta": {
                            "source": f"retinaface:{source_label}",
                            "confidence": float(det.get("score")) if det.get("score") is not None else None,
                            "bbox": [x1, y1, x2, y2],
                            "landmarks": det.get("landmarks"),
                            "aligned": bool(aligned),
                        },
                    })
        except Exception as e:
            print(f"RetinaFace multi-face detection failed on {source_label}: {e}")

    if not found:
        fallback_res = _opencv_face_fallback(img_bgr)
        if fallback_res is not None:
            face112, meta = fallback_res
            bbox = meta.get("bbox") or [0, 0, 0, 0]
            area = max(0, bbox[2] - bbox[0]) * max(0, bbox[3] - bbox[1])
            found.append({
                "face": face112,
                "area": area,
                "meta": {**meta, "source": f"opencv:{source_label}"},
            })

    found.sort(key=lambda f: f["area"], reverse=True)
    return found


def _mask_out_bbox(img_bgr, bbox, pad_ratio=0.15):
    """Black-out a face bbox so a second pass can find the printed ID photo."""
    if img_bgr is None or not bbox or len(bbox) != 4:
        return img_bgr
    out = img_bgr.copy()
    h, w = out.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in bbox]
    bw, bh = max(1, x2 - x1), max(1, y2 - y1)
    px, py = int(pad_ratio * bw), int(pad_ratio * bh)
    x1 = max(0, x1 - px)
    y1 = max(0, y1 - py)
    x2 = min(w, x2 + px)
    y2 = min(h, y2 + py)
    out[y1:y2, x1:x2] = 0
    return out


def _bbox_iou(a, b):
    if not a or not b or len(a) != 4 or len(b) != 4:
        return 0.0
    ax1, ay1, ax2, ay2 = [int(v) for v in a]
    bx1, by1, bx2, by2 = [int(v) for v in b]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    ua = max(1, (ax2 - ax1) * (ay2 - ay1)) + max(1, (bx2 - bx1) * (by2 - by1)) - inter
    return inter / float(ua)


def _nms_faces(faces, iou_thresh=0.40):
    kept = []
    for f in sorted(faces, key=lambda x: x.get("area") or 0, reverse=True):
        bb = (f.get("meta") or {}).get("bbox")
        if any(_bbox_iou(bb, (k.get("meta") or {}).get("bbox")) >= iou_thresh for k in kept):
            continue
        kept.append(f)
    return kept


def _scale_face_hit(hit, scale, ox=0, oy=0):
    """Map a detection from a scaled/cropped ROI back to full-frame coords."""
    meta = dict(hit.get("meta") or {})
    bb = meta.get("bbox")
    if bb and len(bb) == 4:
        meta["bbox"] = [
            int(bb[0] / scale) + ox,
            int(bb[1] / scale) + oy,
            int(bb[2] / scale) + ox,
            int(bb[3] / scale) + oy,
        ]
        x1, y1, x2, y2 = meta["bbox"]
        hit = dict(hit)
        hit["meta"] = meta
        hit["area"] = max(0, x2 - x1) * max(0, y2 - y1)
    return hit


def _opencv_all_faces(img_bgr, min_size=16):
    found = []
    try:
        if not hasattr(cv2, "CascadeClassifier"):
            return found
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        face_cascade = cv2.CascadeClassifier(cascade_path)
        if face_cascade.empty():
            return found
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.08, minNeighbors=3, minSize=(min_size, min_size)
        )
        if faces is None or len(faces) == 0:
            return found
        ih, iw = img_bgr.shape[:2]
        for x, y, w, h in faces:
            det = {"facial_area": [int(x), int(y), int(x + w), int(y + h)], "landmarks": None}
            face112, aligned = _align_and_crop_from_detection(img_bgr, det, crop_mode="tight")
            if face112 is None:
                continue
            found.append({
                "face": face112,
                "area": int(w) * int(h),
                "meta": {
                    "source": "opencv_haar",
                    "confidence": None,
                    "bbox": [int(x), int(y), int(x + w), int(y + h)],
                    "landmarks": None,
                    "aligned": bool(aligned),
                },
            })
    except Exception:
        return found
    return found


def _rois_excluding_holder(iw, ih, bbox, pad_ratio=0.30):
    """Left/right/top/bottom strips around the live face — where a held card sits."""
    x1, y1, x2, y2 = [int(v) for v in bbox]
    bw, bh = max(1, x2 - x1), max(1, y2 - y1)
    hx1 = max(0, x1 - int(bw * pad_ratio))
    hy1 = max(0, y1 - int(bh * pad_ratio))
    hx2 = min(iw, x2 + int(bw * pad_ratio))
    hy2 = min(ih, y2 + int(bh * pad_ratio))
    rois = []
    min_span = 28
    if hx1 >= min_span:
        rois.append((0, 0, hx1, ih, "left"))
    if iw - hx2 >= min_span:
        rois.append((hx2, 0, iw - hx2, ih, "right"))
    if hy1 >= min_span:
        rois.append((0, 0, iw, hy1, "top"))
    if ih - hy2 >= min_span:
        rois.append((0, hy2, iw, ih - hy2, "bottom"))
    return rois


def _face_crop_is_usable(img_bgr):
    """Reject flat/blurry patches that are not a real face photo."""
    if img_bgr is None or getattr(img_bgr, "size", 0) == 0:
        return False
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if len(img_bgr.shape) == 3 else img_bgr
    if gray.shape[0] < 40 or gray.shape[1] < 40:
        return False
    std = float(gray.std())
    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    # Beige wall / motion smear / Haar false-positive: almost no structure.
    return std >= 22.0 and sharp >= 18.0


def _is_retinaface_hit(hit):
    src = str((hit.get("meta") or {}).get("source") or "")
    return "retinaface" in src.lower()


def _pick_id_face(candidates, holder_bbox, holder_area):
    min_area = max(24 * 24, int(holder_area * 0.008))
    max_area = int(holder_area * 0.65)
    scored = []
    hcx = (holder_bbox[0] + holder_bbox[2]) / 2.0
    hcy = (holder_bbox[1] + holder_bbox[3]) / 2.0
    for f in candidates:
        if not _is_retinaface_hit(f):
            continue
        if not _face_crop_is_usable(f.get("face")):
            continue
        area = f.get("area") or 0
        bb = (f.get("meta") or {}).get("bbox") or [0, 0, 0, 0]
        if area < min_area or area > max_area:
            continue
        if _bbox_iou(bb, holder_bbox) >= 0.25:
            continue
        cx = (bb[0] + bb[2]) / 2.0
        cy = (bb[1] + bb[3]) / 2.0
        dist = ((cx - hcx) ** 2 + (cy - hcy) ** 2) ** 0.5
        scored.append((dist, area, f))
    if not scored:
        return None
    return max(scored, key=lambda t: (t[0], t[1]))[2]


def extract_holder_and_id_card_faces(full_bgr, doc_bgr=None, warped_ok=False):
    """
    Step 4.1: person holding an ID card in front of the camera.

      - largest face  → live holder (tight crop, no card in the thumbnail)
      - smaller face  → photo printed on the held ID card
    """
    empty_meta = {
        "source": "none",
        "confidence": None,
        "bbox": None,
        "landmarks": None,
        "aligned": False,
    }
    holder_face = None
    holder_meta = dict(empty_meta)
    id_face = None
    id_meta = dict(empty_meta)

    if full_bgr is None or getattr(full_bgr, "size", 0) == 0:
        return id_face, id_meta, holder_face, holder_meta

    ih, iw = full_bgr.shape[:2]
    collected = []
    collected.extend(_detect_faces_on_image(full_bgr, "frame", crop_mode="tight"))
    try:
        collected.extend(
            _detect_faces_on_image(_apply_clahe(full_bgr, clip_limit=2.0), "frame_clahe", crop_mode="tight")
        )
    except Exception:
        pass

    if max(ih, iw) <= 1400:
        up = cv2.resize(full_bgr, (iw * 2, ih * 2), interpolation=cv2.INTER_CUBIC)
        for hit in _detect_faces_on_image(up, "frame_x2", crop_mode="tight"):
            collected.append(_scale_face_hit(hit, 2.0))

    frame_faces = _nms_faces(collected)
    print(f"[Step4.1] detections={len(collected)} unique={len(frame_faces)}")

    if frame_faces:
        holder_face = frame_faces[0]["face"]
        holder_meta = {**frame_faces[0]["meta"], "role": "holder"}
        holder_area = max(1, frame_faces[0]["area"])
        holder_bbox = holder_meta.get("bbox") or [0, 0, 0, 0]
        pick = _pick_id_face(frame_faces[1:], holder_bbox, holder_area)
        if pick is not None:
            id_face = pick["face"]
            id_meta = {**pick["meta"], "role": "id_card"}

    # Dedicated search: hide the live face and scan the rest of the frame
    # (left/right strips where the user holds the card).
    if id_face is None and holder_meta.get("bbox"):
        holder_bbox = holder_meta["bbox"]
        holder_area = max(1, (holder_bbox[2] - holder_bbox[0]) * (holder_bbox[3] - holder_bbox[1]))
        extras = []
        masked = _mask_out_bbox(full_bgr, holder_bbox, pad_ratio=0.45)
        extras.extend(_detect_faces_on_image(masked, "masked", crop_mode="tight"))
        mh, mw = masked.shape[:2]
        up = cv2.resize(masked, (mw * 2, mh * 2), interpolation=cv2.INTER_CUBIC)
        extras.extend([_scale_face_hit(h, 2.0) for h in _detect_faces_on_image(up, "masked_x2", crop_mode="tight")])
        for ox, oy, rw, rh, tag in _rois_excluding_holder(iw, ih, holder_bbox):
            roi = full_bgr[oy:oy + rh, ox:ox + rw]
            if roi.size == 0 or min(roi.shape[:2]) < 24:
                continue
            for scale, slabel in ((1.0, tag), (2.0, f"{tag}_x2"), (3.0, f"{tag}_x3")):
                view = roi if scale == 1.0 else cv2.resize(
                    roi, (int(rw * scale), int(rh * scale)), interpolation=cv2.INTER_CUBIC
                )
                for hit in _detect_faces_on_image(view, slabel, crop_mode="tight"):
                    extras.append(_scale_face_hit(hit, scale, ox, oy))
        pick = _pick_id_face(_nms_faces(extras), holder_bbox, holder_area)
        if pick is not None:
            id_face = pick["face"]
            id_meta = {**pick["meta"], "role": "id_card"}
            print(f"[Step4.1] ID-card face from {id_meta.get('source')} area={pick['area']}")

    # Warped document crop (if perspective found the card)
    if id_face is None and warped_ok and doc_bgr is not None:
        dh, dw = doc_bgr.shape[:2]
        doc_variants = [("doc", doc_bgr, 1.0)]
        if min(dh, dw) < 700:
            doc_variants.insert(0, ("doc_x2", cv2.resize(doc_bgr, (dw * 2, dh * 2), interpolation=cv2.INTER_CUBIC), 2.0))
            doc_variants.insert(0, ("doc_x3", cv2.resize(doc_bgr, (dw * 3, dh * 3), interpolation=cv2.INTER_CUBIC), 3.0))
        try:
            doc_variants.append(("doc_clahe", _apply_clahe(doc_bgr, clip_limit=2.0), 1.0))
        except Exception:
            pass
        card_hits = []
        for source, candidate, scale in doc_variants:
            hits = _detect_faces_on_image(candidate, source, crop_mode="tight")
            card_area = candidate.shape[0] * candidate.shape[1]
            for pick in hits:
                if pick["area"] > card_area * 0.50:
                    continue
                if pick["area"] < 12 * 12:
                    continue
                card_hits.append(pick)
        if card_hits:
            card_hits.sort(key=lambda f: f["area"], reverse=True)
            pick = card_hits[0]
            id_face = pick["face"]
            id_meta = {**pick["meta"], "role": "id_card"}
            print(f"[Step4.1] ID-card face from warped doc {id_meta.get('source')}")

    print(
        f"[Step4.1] holder={'yes' if holder_face is not None else 'no'} "
        f"id_card={'yes' if id_face is not None else 'no'} "
        f"id_src={id_meta.get('source')}"
    )
    return id_face, id_meta, holder_face, holder_meta


def extract_and_align_face(primary_bgr, original_bgr=None):
    best_face = None
    best_area = 0
    best_meta = {
        "source": "none",
        "confidence": None,
        "bbox": None,
        "landmarks": None,
        "aligned": False,
    }

    # Try RetinaFace across multiple image variants.
    if RetinaFace is not None:
        for source, candidate in _face_detection_candidates(primary_bgr, original_bgr):
            try:
                # Per requested pipeline: preprocess candidate -> convert BGR to RGB
                # before RetinaFace detection.
                rgb_candidate = cv2.cvtColor(candidate, cv2.COLOR_BGR2RGB)
                detections = RetinaFace.detect_faces(rgb_candidate)
                if not detections or not isinstance(detections, dict):
                    continue
                for _, det in detections.items():
                    if not isinstance(det, dict):
                        continue
                    area_box = det.get("facial_area") or [0, 0, 0, 0]
                    if len(area_box) != 4:
                        continue
                    x1, y1, x2, y2 = [int(v) for v in area_box]
                    area = max(0, x2 - x1) * max(0, y2 - y1)
                    if area <= 0:
                        continue
                    face112, aligned = _align_and_crop_from_detection(candidate, det)
                    if face112 is None:
                        continue
                    if area > best_area:
                        best_area = area
                        best_face = face112
                        best_meta = {
                            "source": f"retinaface:{source}",
                            "confidence": float(det.get("score")) if det.get("score") is not None else None,
                            "bbox": [x1, y1, x2, y2],
                            "landmarks": det.get("landmarks"),
                            "aligned": bool(aligned),
                        }
            except Exception as e:
                print(f"RetinaFace face extraction failed on {source}: {e}")

    # Fallback: OpenCV Haar face detector.
    if best_face is None:
        for source, candidate in _face_detection_candidates(primary_bgr, original_bgr):
            fallback_res = _opencv_face_fallback(candidate)
            if fallback_res is not None:
                fallback_face, fallback_meta = fallback_res
                best_face = fallback_face
                best_meta = {
                    **fallback_meta,
                    "source": f"opencv:{source}",
                }
                break

    return best_face, best_meta

# Regex Parsing for Aadhaar Fields
def _digits_only(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _format_aadhaar_display(num12: str) -> str:
    if len(num12) != 12 or not num12.isdigit():
        return num12 or ""
    return f"{num12[:4]} {num12[4:8]} {num12[8:12]}"


def _pick_aadhaar_number(text_lines):
    """
    Pick the printed Aadhaar number from OCR lines.

    Rules:
    - Prefer classic spaced groups: XXXX XXXX XXXX (bottom of card).
    - Strip ALL non-digits before Verhoeff (spaces AND newlines).
    - Never invent alternate digits to "force" Verhoeff pass — that caused
      mismatched numbers to show as VALID after the Level-2 integration fix.
    """
    lines = [l.strip() for l in text_lines if l and str(l).strip()]
    spaced = re.compile(r"(?<!\d)(\d{4})[\s\-]+(\d{4})[\s\-]+(\d{4})(?!\d)")
    compact = re.compile(r"(?<!\d)(\d{12})(?!\d)")

    spaced_candidates = []
    for idx, line in enumerate(lines):
        for m in spaced.finditer(line):
            digits = m.group(1) + m.group(2) + m.group(3)
            spaced_candidates.append((idx, digits, m.group(0)))

    # Prefer the last spaced match — UID is printed near the bottom
    if spaced_candidates:
        spaced_candidates.sort(key=lambda t: t[0])
        digits = spaced_candidates[-1][1]
        return digits, validate_verhoeff(digits)

    compact_candidates = []
    for idx, line in enumerate(lines):
        for m in compact.finditer(line):
            compact_candidates.append((idx, m.group(1)))
        dline = _digits_only(line)
        if len(dline) == 12:
            compact_candidates.append((idx, dline))
        elif len(dline) > 12:
            # sliding 12 within a single line only (avoid cross-line DOB merges)
            for i in range(len(dline) - 11):
                compact_candidates.append((idx, dline[i : i + 12]))

    if compact_candidates:
        compact_candidates.sort(key=lambda t: t[0])
        digits = compact_candidates[-1][1]
        return digits, validate_verhoeff(digits)

    # Last resort: spaced pattern across full text, take last match
    full_text = "\n".join(lines)
    all_spaced = list(spaced.finditer(full_text))
    if all_spaced:
        m = all_spaced[-1]
        digits = m.group(1) + m.group(2) + m.group(3)
        return digits, validate_verhoeff(digits)

    return "", False


def _ocr_aadhaar_number_from_roi(img_np, upload_folder, filename_stem):
    """
    Level-2 style focused pass: OCR only the lower band where the UID is printed.
    Improves digit accuracy without the old aggressive full-frame FSRCNN/sharpen.
    """
    if img_np is None or img_np.size == 0:
        return "", False, []
    h, w = img_np.shape[:2]
    y0, y1 = int(h * 0.52), int(h * 0.88)
    roi = img_np[y0:y1, 0:w]
    if roi.size == 0:
        return "", False, []

    # Upscale ROI for clearer digits (cubic only — no denoise/unsharp)
    rh, rw = roi.shape[:2]
    if min(rh, rw) < 400:
        roi = cv2.resize(roi, (rw * 2, rh * 2), interpolation=cv2.INTER_CUBIC)
    roi = _apply_clahe(roi, clip_limit=1.8)

    tmp = os.path.join(upload_folder, f"_aadhaar_roi_{filename_stem}.jpg")
    try:
        cv2.imwrite(tmp, roi)
        ocr_result = ocr.ocr(tmp)
        lines, _scores = _extract_paddle_lines(ocr_result)
        num, valid = _pick_aadhaar_number(lines)
        return num, valid, lines
    except Exception as e:
        print(f"Aadhaar ROI OCR failed: {e}")
        return "", False, []
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _max_consonant_run(word: str) -> int:
    run = max_run = 0
    for ch in word.lower():
        if ch.isalpha() and ch not in "aeiou":
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    return max_run


def _is_plausible_english_name(line: str) -> bool:
    """Reject Tamil-script OCR garbage misread as Latin (e.g. 'UDSIL IFTHIBLD')."""
    if not line:
        return False
    # Must be mostly ASCII letters / spaces / dots
    if re.search(r"[^\x00-\x7F]", line):
        return False
    cleaned = re.sub(r"[^A-Za-z\s.']", "", line).strip()
    words = [w for w in re.split(r"\s+", cleaned) if w]
    if not (1 <= len(words) <= 5):
        return False
    if not all(re.match(r"^[A-Za-z][A-Za-z.']*$", w) for w in words):
        return False
    letters = re.sub(r"[^A-Za-z]", "", cleaned)
    if len(letters) < 2:
        return False
    vowels = sum(1 for ch in letters.lower() if ch in "aeiou")
    if vowels / len(letters) < 0.18 and len(letters) >= 6:
        return False

    # ALL-CAPS long tokens from Tamil OCR are usually junk — reject consonant soup
    titleish = any(w.istitle() or (len(w) == 1 and w.isupper()) for w in words)
    for w in words:
        if w.isupper() and len(w) >= 5 and not titleish:
            w_letters = re.sub(r"[^A-Za-z]", "", w)
            w_vowels = sum(1 for ch in w_letters.lower() if ch in "aeiou")
            if w_vowels / max(len(w_letters), 1) < 0.22:
                return False
            if _max_consonant_run(w) >= 3:
                return False

    skip = re.compile(
        r"(?i)^(government|india|unique|identification|authority|aadhaar|aadhar|uidai|"
        r"male|female|dob|birth|enrolment|enrollment|issue|date)$"
    )
    if skip.search(cleaned):
        return False
    if re.search(
        r"(?i)(government|india|unique|identification|authority|aadhaar|aadhar|uidai|enrolment)",
        cleaned,
    ):
        return False
    return True


def parse_aadhaar_text(text_lines):
    full_text = "\n".join(text_lines)

    # 1. Aadhaar Number (digit-only + Verhoeff-preferring)
    aadhaar_num, valid_aadhaar = _pick_aadhaar_number(text_lines)

    # 2. Gender
    gender = ""
    if re.search(r"(?i)\b(female|femle|fema)\b", full_text):
        gender = "FEMALE"
    elif re.search(r"(?i)\b(male|mle|mal)\b", full_text):
        gender = "MALE"

    # 3. Date of Birth
    dob = ""
    dob_match = re.search(
        r"(?i)(dob|birth|birthdate|year\s*of\s*birth)\s*:?\s*(\d{2}[/\-]\d{2}[/\-]\d{4}|\d{4})",
        full_text,
    )
    if dob_match:
        dob = dob_match.group(2)
    else:
        # Fallback: first DD/MM/YYYY that is not an issue-date-only cue nearby
        m = re.search(r"\b(\d{2}[/\-]\d{2}[/\-]\d{4})\b", full_text)
        if m:
            dob = m.group(1)

    # 4. Name — prefer English line immediately above DOB; never Tamil OCR junk
    name = ""
    lines = [l.strip() for l in text_lines if l.strip()]
    dob_idx = -1
    for idx, line in enumerate(lines):
        if re.search(r"(?i)(dob|birth|yob)", line) or (
            dob and dob in line
        ):
            dob_idx = idx
            break

    if dob_idx > 0:
        for back in range(1, min(4, dob_idx + 1)):
            candidate = lines[dob_idx - back]
            if re.search(r"(?i)(dob|birth|male|female|yob|father|husband|issue\s*date)", candidate):
                continue
            if _is_plausible_english_name(candidate):
                name = candidate
                break

    if not name:
        for line in lines:
            if re.search(
                r"(?i)(government|india|unique|identification|authority|enrolment|dob|birth|male|female|yob|father|husband|issue\s*date)",
                line,
            ):
                continue
            if _digits_only(line) and len(_digits_only(line)) >= 8:
                continue
            if _is_plausible_english_name(line):
                name = line
                break

    return {
        "document_type": "AADHAAR",
        "name": name,
        "dob": dob,
        "gender": gender,
        "aadhaar_number": _format_aadhaar_display(aadhaar_num) if aadhaar_num else "",
        "aadhaar_number_validated": valid_aadhaar,
    }

# PAN format validation: 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F).
# PAN has no public checksum algorithm (unlike Aadhaar's Verhoeff), so validation
# is a structural/format check plus a sanity check on the 4th character (holder type).
PAN_HOLDER_TYPES = set("PCHABGJLFT")

def validate_pan_format(pan_str: str) -> bool:
    if not pan_str or len(pan_str) != 10:
        return False
    if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan_str):
        return False
    return pan_str[3] in PAN_HOLDER_TYPES

def extract_and_correct_pan(text_lines):
    full_text = ' '.join(text_lines).upper()
    clean_text = re.sub(r'[,.\-_:;]', ' ', full_text)
    words = clean_text.split()
    
    # 1. Look for exact match in words
    for word in words:
        if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', word):
            return word
            
    # 2. Look for 10-char alphanumeric word and try to correct OCR mistakes
    for word in words:
        if len(word) == 10 and word.isalnum():
            corrected = ''
            for char in word[:5]:
                if char == '0': corrected += 'O'
                elif char == '1': corrected += 'I'
                elif char == '5': corrected += 'S'
                elif char == '8': corrected += 'B'
                else: corrected += char
            for char in word[5:9]:
                if char in ('O', 'Q', 'D'): corrected += '0'
                elif char in ('I', 'L'): corrected += '1'
                elif char == 'S': corrected += '5'
                elif char == 'B': corrected += '8'
                elif char == 'Z': corrected += '2'
                else: corrected += char
            char = word[9]
            if char == '0': corrected += 'O'
            elif char == '1': corrected += 'I'
            elif char == '5': corrected += 'S'
            elif char == '8': corrected += 'B'
            else: corrected += char
            
            if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', corrected):
                return corrected

    # 3. Remove all spaces and look for exact match (handles spaces inside PAN)
    text_no_space = re.sub(r'\s+', '', full_text)
    match = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]', text_no_space)
    if match:
        return match.group(0)

    # 4. Sliding window of 10 chars on text_no_space with OCR correction
    text_no_space_clean = re.sub(r'[\s,.\-_:;]', '', full_text)
    for i in range(len(text_no_space_clean) - 9):
        window = text_no_space_clean[i:i+10]
        if window.isalnum():
            corrected = ''
            for j, char in enumerate(window):
                if j < 5:
                    if char == '0': corrected += 'O'
                    elif char == '1': corrected += 'I'
                    elif char == '5': corrected += 'S'
                    elif char == '8': corrected += 'B'
                    else: corrected += char
                elif j < 9:
                    if char in ('O', 'Q', 'D'): corrected += '0'
                    elif char in ('I', 'L'): corrected += '1'
                    elif char == 'S': corrected += '5'
                    elif char == 'B': corrected += '8'
                    elif char == 'Z': corrected += '2'
                    else: corrected += char
                else:
                    if char == '0': corrected += 'O'
                    elif char == '1': corrected += 'I'
                    elif char == '5': corrected += 'S'
                    elif char == '8': corrected += 'B'
                    else: corrected += char
            if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', corrected):
                return corrected

    # 5. Look for any 9-10 char word that is mostly letters/digits (fallback)
    for word in words:
        if 9 <= len(word) <= 10 and word.isalnum():
            letters = sum(c.isalpha() for c in word)
            digits = sum(c.isdigit() for c in word)
            if letters >= 3 and digits >= 2:
                return word

    # 6. Fallback for dummy images that don't have a valid PAN but have a string above Father's Name
    for i, line in enumerate(text_lines):
        if 'NAME' in line.upper():
            prev_lines = text_lines[max(0, i-4):i]
            combined = ''.join(prev_lines).upper()
            combined = re.sub(r'[\s\-.,]', '', combined)
            combined = re.sub(r'(INCOMETAXDEPARTMENT|GOVTOFINDIA|THE)', '', combined)
            if len(combined) >= 6 and any(c.isdigit() for c in combined):
                return combined

    return ''

def detect_document_type(text_lines):
    full_text = " ".join(text_lines).upper()
    text_no_space = re.sub(r'[\s\-.,]', '', full_text)

    pan_keywords = ['INCOMETAXDEPARTMENT', 'PERMANENTACCOUNTNUMBER', 'INCOMETAX', 'GOVTOFINDIA']
    aadhaar_keywords = ['AADHAAR', 'AADHAR', 'UIDAI', 'UNIQUEIDENTIFICATIONAUTHORITY']

    has_pan_keyword = any(kw in text_no_space for kw in pan_keywords)
    has_aadhaar_keyword = any(kw in text_no_space for kw in aadhaar_keywords)

    pan_number_found = bool(extract_and_correct_pan(text_lines))
    aadhaar_number_found = bool(re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', full_text))

    if has_pan_keyword and not has_aadhaar_keyword:
        return "PAN"
    if has_aadhaar_keyword and not has_pan_keyword:
        return "AADHAAR"
    # Fall back to number-pattern-based detection if keywords are ambiguous/missing
    if pan_number_found and not aadhaar_number_found:
        return "PAN"
    if aadhaar_number_found:
        return "AADHAAR"
    if pan_number_found:
        return "PAN"
    return "UNKNOWN"

# Regex Parsing for PAN Card Fields
def parse_pan_text(text_lines):
    full_text = "\n".join(text_lines)

    # 1. PAN Number
    pan_num = extract_and_correct_pan(text_lines)
    valid_pan = validate_pan_format(pan_num)

    # 2. Date of Birth (DD/MM/YYYY or DD-MM-YYYY)
    dob = ""
    dob_match = re.search(r'\b(\d{2}[/\-]\d{2}[/\-]\d{4})\b', full_text)
    if dob_match:
        dob = dob_match.group(1)

    # 3. Name & Father's Name extraction
    # PAN cards typically list Name, then Father's Name, then DOB, in that order.
    name = ""
    father_name = ""
    lines = [l.strip() for l in text_lines if l.strip()]
    
    # Find the line containing "Father"
    father_idx = -1
    for i, line in enumerate(lines):
        if re.search(r'(?i)father', line):
            father_idx = i
            break
            
    if father_idx != -1:
        # Father's name is usually the line immediately below
        if father_idx + 1 < len(lines):
            potential_father = lines[father_idx + 1]
            if not re.search(r'(?i)(date|birth|signature|\d)', potential_father):
                father_name = potential_father
                
        # Name is usually the line immediately above "Father's Name"
        if father_idx - 1 >= 0:
            potential_name = lines[father_idx - 1]
            if not re.search(r'(?i)(name|tax|govt|india|department)', potential_name):
                name = potential_name
            elif father_idx - 2 >= 0:
                potential_name = lines[father_idx - 2]
                if not re.search(r'(?i)(name|tax|govt|india|department)', potential_name):
                    name = potential_name
    else:
        # Fallback if "Father" keyword not found
        skip_pattern = re.compile(r'(?i)(income\s*tax|govt|government|india|permanent\s*account|signature|date\s*of\s*birth|department|card|name)')
        name_candidates = []
        for line in lines:
            if skip_pattern.search(line):
                continue
            if extract_and_correct_pan([line]):
                continue
            if re.search(r'\d{2}[/\-]\d{2}[/\-]\d{4}', line):
                continue
            words = line.split()
            if len(words) >= 1 and all(w.replace('.', '').isalpha() for w in words):
                name_candidates.append(line)
        if len(name_candidates) >= 1:
            name = name_candidates[0]
        if len(name_candidates) >= 2:
            father_name = name_candidates[1]

    return {
        "document_type": "PAN",
        "name": name,
        "father_name": father_name,
        "dob": dob,
        "pan_number": pan_num,
        "pan_number_validated": valid_pan
    }

# Unified entry point: detects whether the document is Aadhaar or PAN and
# dispatches to the appropriate field parser.
def parse_id_document(text_lines, hinted_type=None):
    hint = (hinted_type or "").upper()
    if hint == "PAN":
        return parse_pan_text(text_lines)
    if hint == "AADHAAR":
        return parse_aadhaar_text(text_lines)
    doc_type = detect_document_type(text_lines)
    if doc_type == "PAN":
        return parse_pan_text(text_lines)
    result = parse_aadhaar_text(text_lines)
    if doc_type == "UNKNOWN":
        result["document_type"] = "UNKNOWN"
    return result


def _extract_paddle_lines(ocr_result):
    """Normalize PaddleOCR v2 list / v3 dict results into (lines, scores)."""
    extracted_lines = []
    confidence_scores = []
    if not ocr_result or not isinstance(ocr_result, list):
        return extracted_lines, confidence_scores

    first = ocr_result[0]
    if isinstance(first, dict):
        rec_texts = first.get("rec_texts", []) or []
        rec_scores = first.get("rec_scores", []) or []
        for text, conf in zip(rec_texts, rec_scores):
            extracted_lines.append(text)
            confidence_scores.append(float(conf))
        # If scores missing, still keep texts
        if rec_texts and not confidence_scores:
            extracted_lines = list(rec_texts)
    elif isinstance(first, list):
        for line in first:
            if line and len(line) > 1:
                extracted_lines.append(line[1][0])
                confidence_scores.append(float(line[1][1]))
    return extracted_lines, confidence_scores


def _score_ocr_parse(parsed_fields, avg_confidence, text_lines):
    """Rank OCR candidate passes — prefer valid ID + plausible English name."""
    score = float(avg_confidence or 0.0)
    doc_type = (parsed_fields or {}).get("document_type", "")
    if doc_type == "AADHAAR":
        if parsed_fields.get("aadhaar_number_validated"):
            score += 0.35
        if parsed_fields.get("aadhaar_number"):
            score += 0.1
        name = (parsed_fields.get("name") or "").strip()
        if name and _is_plausible_english_name(name):
            score += 0.25
        # Penalize Tamil→Latin garbage names
        if name and not _is_plausible_english_name(name):
            score -= 0.3
    elif doc_type == "PAN":
        if parsed_fields.get("pan_number_validated"):
            score += 0.35
        if parsed_fields.get("name"):
            score += 0.15
    # Prefer richer English text
    ascii_chars = sum(1 for t in text_lines for ch in t if ch.isascii() and ch.isalpha())
    score += min(ascii_chars, 80) / 400.0
    return score


def run_paddle_ocr_on_image(img_np, tmp_path, hinted_type=None):
    cv2.imwrite(tmp_path, img_np)
    ocr_result = ocr.ocr(tmp_path)
    lines, scores = _extract_paddle_lines(ocr_result)
    avg_conf = float(np.mean(scores)) if scores else 0.0
    parsed = parse_id_document(lines, hinted_type=hinted_type)
    return lines, scores, avg_conf, parsed


def best_ocr_pass(warped_img, upload_folder, filename_stem, hinted_type=None):
    """
    Try mild enhance first, fall back to raw warp if parse quality is weak.
    For Aadhaar, refine the UID with a lower-band ROI OCR so digits aren't
    invented/mismatched while Verhoeff still shows VALID.
    Returns (best_img, lines, scores, avg_conf, parsed, label).
    """
    candidates = prepare_ocr_candidates(warped_img)
    best = None
    for label, img in candidates:
        tmp = os.path.join(upload_folder, f"_ocr_tmp_{label}_{filename_stem}.jpg")
        try:
            lines, scores, avg_conf, parsed = run_paddle_ocr_on_image(img, tmp, hinted_type=hinted_type)
            rank = _score_ocr_parse(parsed, avg_conf, lines)
            print(f"[OCR pass={label}] conf={avg_conf:.3f} rank={rank:.3f} parsed={parsed}")
            item = (rank, label, img, lines, scores, avg_conf, parsed)
            if best is None or item[0] > best[0]:
                best = item
            # Early exit if Aadhaar looks solid
            if (
                parsed.get("document_type") == "AADHAAR"
                and parsed.get("aadhaar_number_validated")
                and _is_plausible_english_name(parsed.get("name") or "")
            ):
                break
            # Same for PAN
            if (
                parsed.get("document_type") == "PAN"
                and parsed.get("pan_number_validated")
                and (parsed.get("name") or "").strip()
            ):
                break
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass

    if best is None:
        empty = enhance_image_for_ocr(warped_img)
        return empty, [], [], 0.0, parse_id_document([], hinted_type=hinted_type), "mild"

    _, label, img, lines, scores, avg_conf, parsed = best
    parsed = dict(parsed or {})

    # Aadhaar UID refinement: OCR the bottom number band on the winning image
    # (and raw warp as backup). Never invent digits — Verhoeff only on OCR text.
    if parsed.get("document_type") in ("AADHAAR", "UNKNOWN"):
        roi_num, roi_valid, roi_lines = _ocr_aadhaar_number_from_roi(
            img, upload_folder, filename_stem
        )
        if not roi_num:
            roi_num, roi_valid, roi_lines = _ocr_aadhaar_number_from_roi(
                warped_img, upload_folder, f"{filename_stem}_raw"
            )
        full_num = _digits_only(parsed.get("aadhaar_number", ""))
        if roi_num:
            print(
                f"[Aadhaar ROI] full={full_num} roi={roi_num} "
                f"roi_valid={roi_valid} roi_lines={roi_lines}"
            )
            # Trust ROI digits for the printed UID; validity = real Verhoeff only
            parsed["aadhaar_number"] = _format_aadhaar_display(roi_num)
            parsed["aadhaar_number_validated"] = bool(roi_valid)
            if parsed.get("document_type") == "UNKNOWN" and roi_num:
                parsed["document_type"] = "AADHAAR"
        elif full_num:
            # Recompute validity on exact digits (no variant invention)
            parsed["aadhaar_number"] = _format_aadhaar_display(full_num)
            parsed["aadhaar_number_validated"] = validate_verhoeff(full_num)

    return img, lines, scores, avg_conf, parsed, label

def load_cv_image(file_path: str):
    """Load JPG/PNG/PDF into a BGR numpy image. cv2.imread fails on Windows paths with spaces."""
    path = os.path.abspath(file_path)
    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        try:
            import fitz
            doc = fitz.open(path)
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            doc.close()
            if pix.n == 3:
                return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            if pix.n == 4:
                return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            return arr
        except Exception as e:
            print(f"PDF render failed: {e}")
            return None

    try:
        from PIL import ImageOps
        with Image.open(path) as pil:
            pil = ImageOps.exif_transpose(pil)
            rgb = pil.convert("RGB")
            return cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)
    except Exception:
        pass

    try:
        data = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is not None:
            return img
    except Exception:
        pass

    img = cv2.imread(path)
    return img if img is not None else None


@app.route('/health')
def ocr_health():
    return jsonify({"status": "ok", "service": "ocr"})


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/live')
def live_verification():
    return render_template_string(STEP2_HTML_TEMPLATE)

_RECENT_OCR_FACES = []


def _remember_ocr_face(filename):
    if not filename:
        return
    name = os.path.basename(str(filename))
    if name in _RECENT_OCR_FACES:
        _RECENT_OCR_FACES.remove(name)
    _RECENT_OCR_FACES.append(name)
    del _RECENT_OCR_FACES[:-8]


def _resolve_upload_face_path(filename):
    """Resolve a face filename inside the OCR upload folder."""
    if not filename:
        return None
    name = os.path.basename(str(filename).strip())
    try:
        from urllib.parse import unquote
        name = unquote(name)
    except Exception:
        pass
    if not name or name in (".", ".."):
        return None
    path = os.path.join(app.config["UPLOAD_FOLDER"], name)
    return path if os.path.isfile(path) else None


def _recent_uploaded_face_files():
    """Faces saved from document OCR in this process (not live Step 4.1 crops)."""
    names = []
    seen = set()
    for name in list(_RECENT_OCR_FACES)[::-1]:
        path = _resolve_upload_face_path(name)
        if path and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _verify_face_pair(path_a, path_b):
    """
    Cross-verify two already-cropped face images with ArcFace.
    Pixel similarity is NOT used for MATCHED — it rubber-stamps skin patches.
    """
    if not path_a or not path_b:
        return None
    img_a = cv2.imread(path_a)
    img_b = cv2.imread(path_b)
    if not _face_crop_is_usable(img_a) or not _face_crop_is_usable(img_b):
        print(f"[face_match] skipped (not a usable face crop): {os.path.basename(path_a)} vs {os.path.basename(path_b)}")
        return {
            "verified": False,
            "distance": None,
            "threshold": None,
            "model": None,
            "error": "crop_not_a_face",
        }
    if DeepFace is None:
        print("[face_match] DeepFace/ArcFace not loaded — cannot verify")
        return {
            "verified": False,
            "distance": None,
            "threshold": None,
            "model": None,
            "error": "arcface_unavailable",
        }
    try:
        result = DeepFace.verify(
            img1_path=path_a,
            img2_path=path_b,
            model_name="ArcFace",
            enforce_detection=False,
        )
        verified = bool(result.get("verified", False))
        dist = float(result["distance"]) if result.get("distance") is not None else None
        thr = float(result["threshold"]) if result.get("threshold") is not None else None
        print(
            f"[face_match] ArcFace verified={verified} d={dist} thr={thr} "
            f"{os.path.basename(path_a)} vs {os.path.basename(path_b)}"
        )
        return {
            "verified": verified,
            "distance": dist,
            "threshold": thr,
            "model": "ArcFace",
        }
    except Exception as e1:
        print(f"ArcFace verify failed ({e1})")
        return {
            "verified": False,
            "distance": None,
            "threshold": None,
            "model": None,
            "error": str(e1),
        }


def _collect_reference_faces(data):
    """
    Uploaded-document face crops used as Step-1 / Step-3 references.
    Accepts step1_face (string) and/or step3_faces (list).
    """
    refs = []
    seen = set()

    def _add(label, raw):
        name = os.path.basename(str(raw or "").strip())
        if not name or name in seen:
            return
        path = _resolve_upload_face_path(name)
        if not path:
            return
        seen.add(name)
        refs.append({"label": label, "filename": name, "path": path})

    step1 = data.get("step1_face") if isinstance(data, dict) else None
    if step1:
        _add("step1", step1)

    step3 = data.get("step3_faces") if isinstance(data, dict) else None
    if isinstance(step3, list):
        for item in step3:
            _add("step3", item)

    if not refs:
        for name in _recent_uploaded_face_files():
            _add("ocr_cache", name)
        if refs:
            print(f"[live_verify] No client face names; using {len(refs)} OCR face(s) from cache/disk")

    return refs


def _cross_verify_uploaded_vs_live(refs, holder_filename, id_filename):
    """
    Cross-verify each uploaded face against:
      - live holder face (person in front of camera)  → primary identity match
      - live ID-card printed face                    → card photo match

    face_match (overall) is True when ANY uploaded face matches the live HOLDER.
    """
    holder_path = _resolve_upload_face_path(holder_filename)
    id_path = _resolve_upload_face_path(id_filename)

    details = []
    any_holder_match = None
    any_id_match = None

    for ref in refs:
        row = {
            "reference": ref["filename"],
            "source": ref["label"],
            "vs_holder": None,
            "vs_id_card": None,
        }
        if holder_path:
            vh = _verify_face_pair(ref["path"], holder_path)
            row["vs_holder"] = vh
            if vh is not None and "error" not in vh:
                if vh.get("verified"):
                    any_holder_match = True
                elif any_holder_match is None:
                    any_holder_match = False
        if id_path:
            vi = _verify_face_pair(ref["path"], id_path)
            row["vs_id_card"] = vi
            if vi is not None and "error" not in vi:
                if vi.get("verified"):
                    any_id_match = True
                elif any_id_match is None:
                    any_id_match = False
        details.append(row)

    return {
        "face_match": any_holder_match,  # Step1/upload vs live person
        "face_match_vs_holder": any_holder_match,
        "face_match_vs_id_card": any_id_match,
        "face_match_details": details,
        # Back-compat list used by portal UI
        "step3_face_matches": [
            {
                "step3_face": d["reference"],
                "verified": bool((d.get("vs_holder") or {}).get("verified"))
                or bool((d.get("vs_id_card") or {}).get("verified")),
                "vs_holder": d.get("vs_holder"),
                "vs_id_card": d.get("vs_id_card"),
                "distance": (d.get("vs_holder") or {}).get("distance"),
                "threshold": (d.get("vs_holder") or {}).get("threshold"),
            }
            for d in details
        ],
    }


@app.route('/api/v1/live_verify', methods=['POST'])
def live_verify_api():
    data = request.json
    if not data or 'image' not in data:
        return jsonify({"error": "No image data provided"}), 400
        
    try:
        # Decode base64 image
        image_data = data['image'].split(',')[1]
        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({"error": "Invalid image data"}), 400

        filename_id = str(uuid.uuid4())
        
        # ── Face extraction (RetinaFace) ──────────────────────────────────
        # Live frame → two faces:
        #   A) live holder (largest face)
        #   B) printed photo on the ID card being held (smaller face)
        doc_img, warped_ok = detect_and_warp_document(img)
        id_face_img, id_face_meta, holder_face_img, holder_face_meta = (
            extract_holder_and_id_card_faces(img, doc_img, warped_ok)
        )

        if id_face_img is not None and not _face_crop_is_usable(id_face_img):
            print(f"[Step4.1] dropping unusable ID-card crop src={id_face_meta.get('source')}")
            id_face_img = None
            id_face_meta = {**id_face_meta, "source": "rejected_not_a_face"}
        id_face_filename = None
        if id_face_img is not None:
            candidate = f"live_id_face_{filename_id}.jpg"
            id_face_path = os.path.join(app.config['UPLOAD_FOLDER'], candidate)
            if _save_jpg(id_face_path, id_face_img):
                id_face_filename = candidate

        holder_face_filename = None
        if holder_face_img is not None:
            candidate = f"live_holder_face_{filename_id}.jpg"
            holder_face_path = os.path.join(app.config['UPLOAD_FOLDER'], candidate)
            if _save_jpg(holder_face_path, holder_face_img):
                holder_face_filename = candidate

        # OCR on the held document region
        best_img, extracted_lines, _scores, _avg, parsed_fields, _label = best_ocr_pass(
            doc_img, app.config['UPLOAD_FOLDER'], filename_id
        )

        doc_filename = f"live_doc_{filename_id}.jpg"
        doc_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_filename)
        if not _save_jpg(doc_path, best_img):
            return jsonify({"status": "failed", "error": "Failed to save processed live document image"}), 500

        # ── Cross-verification ────────────────────────────────────────────
        # Uploaded doc face(s)  ↔  live holder face  (primary)
        # Uploaded doc face(s)  ↔  live ID-card face (secondary)
        refs = _collect_reference_faces(data)
        match_payload = _cross_verify_uploaded_vs_live(
            refs, holder_face_filename, id_face_filename
        )

        live_vs_id = None
        if holder_face_filename and id_face_filename:
            live_vs_id = _verify_face_pair(
                _resolve_upload_face_path(holder_face_filename),
                _resolve_upload_face_path(id_face_filename),
            )

        from ocr.quality import assess_live_frame, ocr_fields_usable
        quality = assess_live_frame(img)
        missing = []
        if not holder_face_filename:
            missing.append("live_face")
        if not id_face_filename:
            missing.append("id_card_face")
        if not ocr_fields_usable(parsed_fields):
            missing.append("ocr_fields")
        step41_complete = len(missing) == 0

        return jsonify(_json_safe({
            "status": "success" if step41_complete else "incomplete",
            "step41_complete": step41_complete,
            "step41_missing": missing,
            "quality": quality,
            "document_detected": bool(warped_ok),
            "face_image_url": f"/ocr_uploads/{id_face_filename}" if id_face_filename else None,
            "id_card_face_image_url": f"/ocr_uploads/{id_face_filename}" if id_face_filename else None,
            "holder_face_image_url": f"/ocr_uploads/{holder_face_filename}" if holder_face_filename else None,
            "face_source": id_face_meta.get("source"),
            "face_debug": id_face_meta,
            "holder_face_debug": holder_face_meta,
            "processed_image_url": f"/ocr_uploads/{doc_filename}",
            "parsed_fields": parsed_fields,
            "raw_text": extracted_lines,
            "face_match": match_payload["face_match"],
            "face_match_vs_holder": match_payload["face_match_vs_holder"],
            "face_match_vs_id_card": match_payload["face_match_vs_id_card"],
            "face_match_live_vs_id": live_vs_id,
            "face_match_details": match_payload["face_match_details"],
            "step3_face_matches": match_payload["step3_face_matches"],
            "reference_faces_used": [r["filename"] for r in refs],
        }))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "failed", "error": str(e)}), 500

@app.route('/api/v1/ocr', methods=['POST'])
def run_ocr():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    hinted_type = (request.form.get("document_type") or "").strip().upper() or None

    try:
        img = load_cv_image(file_path)
        if img is None:
            return jsonify({"error": "Invalid image or PDF format"}), 400

        # Step 1: Quality Check
        quality_report = check_image_quality(img)

        # Step 2: Document Detection & Warp
        warped_img, warped_ok = detect_and_warp_document(img)

        stem = os.path.splitext(filename)[0]

        # Step 3: Face extraction pipeline (same rules as Step 4.1)
        # Input -> preprocess (resize/perspective) -> RetinaFace -> bbox -> crop ->
        # align (eye landmarks) -> resize 112x112 -> save temp image.
        face_img, face_meta = extract_and_align_face(warped_img, img)
        face_filename = None
        if face_img is not None:
            candidate = f"aadhaar_face_{stem}.jpg"
            face_path = os.path.join(app.config['UPLOAD_FOLDER'], candidate)
            if _save_jpg(face_path, face_img):
                face_filename = candidate
                _remember_ocr_face(face_filename)

        # Step 4: OCR-safe enhance + dual-pass PaddleOCR (mild vs raw)
        processed_img, extracted_lines, confidence_scores, avg_confidence, parsed_fields, ocr_pass = best_ocr_pass(
            warped_img, app.config['UPLOAD_FOLDER'], stem, hinted_type=hinted_type
        )

        # Save the pipeline image used for the winning OCR pass
        pipeline_filename = f"processed_{stem}.jpg"
        pipeline_path = os.path.join(app.config['UPLOAD_FOLDER'], pipeline_filename)
        if not _save_jpg(pipeline_path, processed_img):
            return jsonify({"status": "failed", "error": "Failed to save OCR processed image"}), 500

        return jsonify(_json_safe({
            "status": "success",
            "quality_check": quality_report,
            "perspective_corrected": warped_ok,
            "ocr_pass": ocr_pass,
            "raw_text": extracted_lines,
            "ocr_confidence": round(float(avg_confidence) * 100, 2),
            "parsed_fields": parsed_fields,
            "processed_image_url": f"/ocr_uploads/{pipeline_filename}",
            "face_image_url": f"/ocr_uploads/{face_filename}" if face_filename else None,
            "face_source": face_meta.get("source"),
            "face_debug": face_meta,
        }))

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error details: {repr(e)}")
        return jsonify({"status": "failed", "error": str(e)}), 500

@app.route('/ocr_uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # Standalone Flask on 5001 is optional. The product entrypoint is:
    #   python main.py   → everything on http://127.0.0.1:8080
    print("OCR is in-process on the portal. Start the app with: python main.py")
    print("(Optional standalone) OCR_STANDALONE=1 python -m ocr.engine")
    if os.getenv("OCR_STANDALONE", "").strip() in ("1", "true", "yes"):
        app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
