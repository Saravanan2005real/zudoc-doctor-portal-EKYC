const API_BASE = window.location.origin;
const videoEl = document.getElementById('live-id-webcam');
const canvasEl = document.getElementById('live-id-canvas');
const btnCapture = document.getElementById('btn-capture-live-id');
const btnRetry = document.getElementById('btn-retry');
const tickEl = document.getElementById('live-id-tick');
const resultPanel = document.getElementById('result-panel');
const spinner = document.getElementById('loading-spinner');

// Step 1 Elements
const btnProcessUpload = document.getElementById('btn-process-upload');
const docUpload = document.getElementById('doc-upload');
const uploadSpinner = document.getElementById('upload-spinner');
const uploadResults = document.getElementById('upload-results');
const step2Section = document.getElementById('step2-live-section');

// Global State
let uploadedDocumentId = null;
let uploadedFaceFilename = null;

// Start Camera — request HD resolution for better OCR accuracy
async function startCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'user',
                width: { ideal: 1280 },
                height: { ideal: 720 },
            },
            audio: false,
        });
        videoEl.srcObject = stream;
    } catch (err) {
        console.error('Camera access denied:', err);
        alert('Camera is required for this demo.');
    }
}

// Grab Frame — use high quality JPEG for OCR
function grabFrameDataUrl() {
    canvasEl.width = videoEl.videoWidth;
    canvasEl.height = videoEl.videoHeight;
    const ctx = canvasEl.getContext('2d');
    ctx.drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);
    return canvasEl.toDataURL('image/jpeg', 0.95);
}

// -------------------------------------------------------------
// STEP 1: Process Uploaded Document
// -------------------------------------------------------------
async function processUploadedDocument() {
    if (!docUpload.files || docUpload.files.length === 0) {
        alert("Please select a document image first.");
        return;
    }

    const file = docUpload.files[0];
    const formData = new FormData();
    formData.append("file", file);

    btnProcessUpload.disabled = true;
    uploadSpinner.classList.remove('hidden');
    uploadResults.classList.add('hidden');
    
    // Reset state
    uploadedDocumentId = null;
    uploadedFaceFilename = null;
    step2Section.style.opacity = '0.4';
    step2Section.style.pointerEvents = 'none';

    try {
        const resp = await fetch(`${API_BASE}/api/v1/ocr`, {
            method: 'POST',
            body: formData,
        });

        const data = await resp.json();

        if (!resp.ok) {
            throw new Error(data.error || data.detail || `HTTP ${resp.status}`);
        }

        const fields = data.parsed_fields || {};
        const idNum = fields.aadhaar_number || fields.pan_number || fields.id_number || fields.dl_number;
        
        if (!idNum) {
            throw new Error("Could not extract a valid ID number from this document. Please try a clearer image.");
        }

        // Store state for step 2 cross-verification
        uploadedDocumentId = idNum;
        if (data.face_image_url) {
            // Extract just the filename (e.g. from "/ocr_uploads/_face_123.jpg")
            const parts = data.face_image_url.split('/');
            uploadedFaceFilename = decodeURIComponent(parts[parts.length - 1]);
        }

        // Render Step 1 Results
        let html = `<h4>✅ Document Processed Successfully</h4>`;
        html += `<p><strong>Extracted ID Number:</strong> ${idNum}</p>`;
        if (fields.name) html += `<p><strong>Name:</strong> ${fields.name}</p>`;
        
        if (data.face_image_url) {
            html += `<div style="margin-top: 12px;">
                <p style="margin-bottom: 4px;"><strong>Extracted Face:</strong></p>
                <img src="${API_BASE}${data.face_image_url}" alt="Extracted ID Face" style="width: 100px; height: 100px; object-fit: cover; border-radius: 8px; border: 2px solid var(--border-color);">
            </div>`;
        } else {
            html += `<p style="color:#ef4444; margin-top: 12px;"><strong>Warning:</strong> No face photo was extracted from this document. Face match in Step 2 will not be possible.</p>`;
        }

        uploadResults.innerHTML = html;
        uploadResults.classList.remove('hidden');

        // Enable Step 2
        step2Section.style.opacity = '1';
        step2Section.style.pointerEvents = 'auto';

    } catch (error) {
        uploadResults.innerHTML = `
            <h4>❌ Upload Processing Failed</h4>
            <p style="color: #ef4444;">${error.message}</p>
        `;
        uploadResults.classList.remove('hidden');
    } finally {
        uploadSpinner.classList.add('hidden');
        btnProcessUpload.disabled = false;
    }
}

// -------------------------------------------------------------
// STEP 2: Capture and Cross Verify Live ID
// -------------------------------------------------------------
async function captureAndVerifyLiveId() {
    if (!videoEl || videoEl.readyState < 2) {
        alert('Camera is not ready yet. Allow camera access and try again.');
        return;
    }

    btnCapture.disabled = true;
    tickEl.classList.remove('hidden');
    spinner.classList.remove('hidden');
    resultPanel.classList.add('hidden');
    btnRetry.classList.add('hidden');

    const dataUrl = grabFrameDataUrl();
    const payload = { image: dataUrl };
    
    // Inject the uploaded face for cross verification
    if (uploadedFaceFilename) {
        payload.step1_face = uploadedFaceFilename;
    }

    try {
        const resp = await fetch(`${API_BASE}/api/v1/live_verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const data = await resp.json();

        if (!resp.ok) {
            throw new Error(data.error || data.detail || `HTTP ${resp.status}`);
        }

        renderResult(data);

    } catch (error) {
        resultPanel.innerHTML = `
            <h4>❌ Detection Failed</h4>
            <p style="color: #ef4444;">${error.message}</p>
        `;
        resultPanel.classList.remove('hidden');
    } finally {
        spinner.classList.add('hidden');
        btnRetry.classList.remove('hidden');
    }
}

function renderResult(data) {
    let html = '';

    // --- Section 1: Face Match Cross Verification ---
    const holderDetected = !!data.holder_face_image_url;
    html += `<h4>Live Verification Results</h4>`;

    // Find the cross verification against the uploaded step1 face
    let fmStep1 = null;
    if (data.step3_face_matches && uploadedFaceFilename) {
        const match = data.step3_face_matches.find(m => m.step3_face === uploadedFaceFilename);
        if (match && match.vs_holder) {
            fmStep1 = match.vs_holder;
        }
    }

    if (fmStep1) {
        // This checks the uploaded step1 face vs live holder
        const matchBadge = fmStep1.verified
            ? '<span class="badge badge-success">MATCH PASSED</span>'
            : '<span class="badge badge-danger">MATCH FAILED</span>';
        html += `<p style="font-size: 1.05rem;"><strong>Face Verification (Live ↔ Uploaded):</strong> ${matchBadge}</p>`;
        if (fmStep1.distance != null) {
            html += `<p style="color:#888; font-size: 0.85rem; margin-top: -4px; margin-bottom: 12px;">Distance: ${fmStep1.distance.toFixed(3)} / Threshold: ${fmStep1.threshold.toFixed(3)}</p>`;
        }
    } else {
        html += `<p><strong>Face Verification:</strong> <span class="badge badge-danger">NOT TESTED</span> (Missing face in upload or live feed)</p>`;
    }

    // --- Section 2: Extraction Details ---
    html += `<h4>Live Frame Details</h4>`;
    
    const faceStatus = holderDetected
        ? '<span class="badge badge-success">LIVE PERSON DETECTED</span>'
        : '<span class="badge badge-danger">NO PERSON DETECTED</span>';
    html += `<p>Liveness Check: ${faceStatus}</p>`;

    // Face images
    if (data.holder_face_image_url || uploadedFaceFilename) {
        html += `<div class="face-images" style="margin-top: 12px;">`;
        if (uploadedFaceFilename) {
            html += `<div><img src="${API_BASE}/ocr_uploads/${uploadedFaceFilename}" alt="Extracted ID Face" style="width: 100px; height: 100px; object-fit: cover; border-radius: 8px; border: 2px solid var(--border-color);"><br><small>Extracted ID Face</small></div>`;
        }
        if (data.holder_face_image_url) {
            html += `<div><img src="${API_BASE}${data.holder_face_image_url}" alt="Holder Face" style="width: 100px; height: 100px; object-fit: cover; border-radius: 8px; border: 2px solid var(--border-color);"><br><small>Live Webcam Face</small></div>`;
        }
        html += `</div>`;
    }

    // Overall status
    html += `<hr style="margin: 20px 0; border: 0; border-top: 1px solid rgba(0,0,0,0.1);">`;
    // The frame is valid as long as a person was detected and the face matched.
    const overallValid = holderDetected && fmStep1 && fmStep1.verified;
    
    const overallBadge = overallValid
        ? '<span class="badge badge-success">VERIFICATION SUCCESSFUL</span>'
        : '<span class="badge badge-danger">VERIFICATION FAILED</span>';
    html += `<p style="font-size: 1.1rem; font-weight: bold;">Final Verdict: ${overallBadge}</p>`;

    resultPanel.innerHTML = html;
    resultPanel.classList.remove('hidden');
}

btnProcessUpload.addEventListener('click', processUploadedDocument);
btnCapture.addEventListener('click', captureAndVerifyLiveId);
btnRetry.addEventListener('click', () => {
    tickEl.classList.add('hidden');
    resultPanel.classList.add('hidden');
    btnRetry.classList.add('hidden');
    btnCapture.disabled = false;
});

// Init
window.addEventListener('load', startCamera);
