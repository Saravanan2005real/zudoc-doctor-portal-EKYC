"""
Aadhaar Card OCR Service — PaddleOCR Microservice
Port: 5001
"""

import os
import sys
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

# Disable oneDNN/MKLDNN to prevent the PIR implementation bug on CPU
os.environ['FLAGS_use_mkldnn'] = '0'
# Use legacy keras for retinaface compatibility with TF 2.15+
os.environ['TF_USE_LEGACY_KERAS'] = '1'
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
sys.stdout, sys.stderr = io.StringIO(), io.StringIO()

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

try:
    from ultralytics import YOLO
    yolo_model = YOLO('yolov8n.pt') # Placeholder for document detection model
except Exception as e:
    # Suppress YOLO load error output to keep logs clean
    yolo_model = None

try:
    from retinaface import RetinaFace
except Exception as e:
    print(f"RetinaFace load failed: {e}")
    RetinaFace = None

# Restore stdout/stderr
sys.stdout, sys.stderr = _old_stdout, _old_stderr

# Suppress paddlex logger
import logging
paddlex_logger = logging.getLogger('paddlex')
paddlex_logger.setLevel(logging.ERROR)
for handler in paddlex_logger.handlers:
    paddlex_logger.removeHandler(handler)

app = Flask(__name__)
CORS(app)


# Ensure upload directory exists
UPLOAD_FOLDER = './ocr_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
                        const faceImg = document.getElementById('extracted-face');
                        faceImg.src = data.face_image_url;
                        document.getElementById('face-card').style.display = 'block';
                    } else {
                        document.getElementById('face-card').style.display = 'none';
                    }

                    results.style.display = 'block';
                    
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
                            <span class="field-name">Name</span>
                            <span class="field-val" id="res-name">-</span>
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
            
            // Mirror the canvas context to match the mirrored video element
            ctx.translate(canvas.width, 0);
            ctx.scale(-1, 1);
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
                    body: JSON.stringify({ image: base64Image })
                });
                const data = await resp.json();
                
                if (data.status === 'success') {
                    const docType = data.parsed_fields.document_type || 'UNKNOWN';
                    const docBadge = document.getElementById('doc-type-badge');
                    docBadge.innerText = docType === 'PAN' ? 'PAN CARD' : (docType === 'AADHAAR' ? 'AADHAAR CARD' : 'UNKNOWN');
                    docBadge.className = 'badge ' + (docType === 'UNKNOWN' ? 'badge-error' : 'badge-success');

                    document.getElementById('res-name').innerText = data.parsed_fields.name || 'Not Found';

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
    # Load OpenCV's pre-trained Haar cascade for frontal face
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    face_visible = False
    face_not_cropped = True
    face_not_too_small = True

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

# Brightness Correction
def correct_brightness(img_np):
    # Apply CLAHE to L channel of LUV or LAB color space
    lab = cv2.cvtColor(img_np, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    return enhanced

# Face Extraction & Alignment using RetinaFace
def extract_and_align_face(img_np):
    if RetinaFace is None:
        return None
    try:
        # RetinaFace.extract_faces returns a list of RGB numpy arrays of extracted faces
        # align=True ensures the face is aligned based on eye landmarks
        # expand_face_area=100 adds a 100% margin around the detected face so it captures the full head
        faces = RetinaFace.extract_faces(img_path=img_np, align=True, expand_face_area=100)
        if faces and len(faces) > 0:
            # Find the largest face (assuming it's the main photo on the ID)
            largest_face = max(faces, key=lambda f: f.shape[0] * f.shape[1])
            # Resize to 112x112 as requested
            resized_face = cv2.resize(largest_face, (112, 112))
            # Convert back to BGR for cv2.imwrite
            bgr_face = cv2.cvtColor(resized_face, cv2.COLOR_RGB2BGR)
            return bgr_face
    except Exception as e:
        print(f"Face extraction failed: {e}")
    return None

# Regex Parsing for Aadhaar Fields
def parse_aadhaar_text(text_lines):
    full_text = "\n".join(text_lines)
    
    # 1. Aadhaar Number
    aadhaar_pattern = re.compile(r'\b\d{4}\s\d{4}\s\d{4}\b|\b\d{12}\b')
    aadhaar_matches = aadhaar_pattern.findall(full_text)
    aadhaar_num = ""
    valid_aadhaar = False
    
    if aadhaar_matches:
        aadhaar_num = aadhaar_matches[0].replace(" ", "")
        valid_aadhaar = validate_verhoeff(aadhaar_num)

    # 2. Gender
    gender = ""
    if re.search(r'(?i)\b(female|femle|fema)\b', full_text):
        gender = "FEMALE"
    elif re.search(r'(?i)\b(male|mle|mal)\b', full_text):
        gender = "MALE"

    # 3. Date of Birth
    dob = ""
    dob_match = re.search(r'(?i)(dob|birth|birthdate|year\s*of\s*birth)\s*:?\s*(\d{2}[/\-]\d{2}[/\-]\d{4}|\d{4})', full_text)
    if dob_match:
        dob = dob_match.group(2)

    # 4. Name extraction logic
    name = ""
    # Usually name resides above the DOB line or contains titles
    lines = [l.strip() for l in text_lines if l.strip()]
    for idx, line in enumerate(lines):
        if re.search(r'(?i)(government|india|unique|identification|authority|enrolment)', line):
            continue
        if re.search(r'(?i)(dob|birth|male|female|yob|father|husband)', line):
            continue
        # Names are generally capitalized and contain 2-3 words
        words = line.split()
        if len(words) >= 2 and len(words) <= 4 and all(w[0].isupper() for w in words if w.isalpha()):
            name = line
            break

    return {
        "document_type": "AADHAAR",
        "name": name,
        "dob": dob,
        "gender": gender,
        "aadhaar_number": aadhaar_num,
        "aadhaar_number_validated": valid_aadhaar
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
    
    for word in words:
        if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', word):
            return word
            
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
                elif char in ('I', 'L', 'T'): corrected += '1'
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

    text_no_space = re.sub(r'\s+', '', full_text)
    match = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]', text_no_space)
    if match:
        return match.group(0)

    for word in words:
        if 9 <= len(word) <= 10 and word.isalnum():
            letters = sum(c.isalpha() for c in word)
            digits = sum(c.isdigit() for c in word)
            if letters >= 3 and digits >= 2:
                return word

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
    skip_pattern = re.compile(r'(?i)(income\s*tax|govt|government|india|permanent\s*account|signature|date\s*of\s*birth|department|card)')
    name_candidates = []
    for line in lines:
        if skip_pattern.search(line):
            continue
        if extract_and_correct_pan([line]):
            continue
        if re.search(r'\d{2}[/\-]\d{2}[/\-]\d{4}', line):
            continue
        words = line.split()
        if len(words) >= 2 and all(w.replace('.', '').isalpha() for w in words):
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
def parse_id_document(text_lines):
    doc_type = detect_document_type(text_lines)
    if doc_type == "PAN":
        return parse_pan_text(text_lines)
    result = parse_aadhaar_text(text_lines)
    if doc_type == "UNKNOWN":
        result["document_type"] = "UNKNOWN"
    return result

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/live')
def live_verification():
    return render_template_string(STEP2_HTML_TEMPLATE)

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
        
        # 1. Face Extraction (RetinaFace)
        face_img = extract_and_align_face(img)
        face_filename = None
        if face_img is not None:
            face_filename = f"live_face_{filename_id}.jpg"
            face_path = os.path.join(app.config['UPLOAD_FOLDER'], face_filename)
            cv2.imwrite(face_path, face_img)

        # 2. Document Detection & Warp
        doc_img, warped_ok = detect_and_warp_document(img)
        doc_img = correct_brightness(doc_img)

        doc_filename = f"live_doc_{filename_id}.jpg"
        doc_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_filename)
        cv2.imwrite(doc_path, doc_img)
        
        ocr_result = ocr.ocr(doc_path)
        
        extracted_lines = []
        if ocr_result and isinstance(ocr_result, list):
            if isinstance(ocr_result[0], dict):
                res_dict = ocr_result[0]
                rec_texts = res_dict.get('rec_texts', [])
                for text in rec_texts:
                    extracted_lines.append(text)
            elif isinstance(ocr_result[0], list):
                for line in ocr_result[0]:
                    if line and len(line) > 1:
                        extracted_lines.append(line[1][0])

        parsed_fields = parse_id_document(extracted_lines)

        return jsonify({
            "status": "success",
            "face_image_url": f"/ocr_uploads/{face_filename}" if face_filename else None,
            "processed_image_url": f"/ocr_uploads/{doc_filename}",
            "parsed_fields": parsed_fields,
            "raw_text": extracted_lines
        })
        
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

    try:
        # Load image using OpenCV
        img = cv2.imread(file_path)
        if img is None:
            return jsonify({"error": "Invalid image format"}), 400

        # Step 1: Quality Check
        quality_report = check_image_quality(img)

        # Step 2: Document Detection & Warp
        processed_img, warped_ok = detect_and_warp_document(img)

        # Step 3: Brightness Correction
        processed_img = correct_brightness(processed_img)

        # Step 3.5: Extract Face using RetinaFace
        face_img = extract_and_align_face(processed_img)
        face_filename = None
        if face_img is not None:
            face_filename = f"aadhaar_face_{filename}.jpg"
            face_path = os.path.join(app.config['UPLOAD_FOLDER'], face_filename)
            cv2.imwrite(face_path, face_img)

        # Save the pipeline image for verification
        pipeline_filename = f"processed_{filename}"
        pipeline_path = os.path.join(app.config['UPLOAD_FOLDER'], pipeline_filename)
        cv2.imwrite(pipeline_path, processed_img)

        # Step 4: PaddleOCR Extraction
        ocr_result = ocr.ocr(pipeline_path)
        
        extracted_lines = []
        confidence_scores = []
        if ocr_result and isinstance(ocr_result, list):
            # Check if it's the new dictionary format (PaddleX / PaddleOCR v3+)
            if isinstance(ocr_result[0], dict):
                res_dict = ocr_result[0]
                rec_texts = res_dict.get('rec_texts', [])
                rec_scores = res_dict.get('rec_scores', [])
                for text, conf in zip(rec_texts, rec_scores):
                    extracted_lines.append(text)
                    confidence_scores.append(conf)
            elif isinstance(ocr_result[0], list):
                # Old format: [[[box], [text, conf]], ...]
                for line in ocr_result[0]:
                    if line and len(line) > 1:
                        text = line[1][0]
                        conf = line[1][1]
                        extracted_lines.append(text)
                        confidence_scores.append(conf)

        avg_confidence = float(np.mean(confidence_scores)) if confidence_scores else 0.0

        # Step 5: Regex Parsing (auto-detects Aadhaar vs PAN)
        parsed_fields = parse_id_document(extracted_lines)

        return jsonify({
            "status": "success",
            "quality_check": quality_report,
            "perspective_corrected": warped_ok,
            "raw_text": extracted_lines,
            "ocr_confidence": round(avg_confidence * 100, 2),
            "parsed_fields": parsed_fields,
            "processed_image_url": f"/ocr_uploads/{pipeline_filename}",
            "face_image_url": f"/ocr_uploads/{face_filename}" if face_filename else None
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error details: {repr(e)}")
        return jsonify({"status": "failed", "error": str(e)}), 500

@app.route('/ocr_uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
