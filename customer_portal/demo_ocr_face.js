const API_BASE = window.location.origin;
const videoEl = document.getElementById('live-id-webcam');
const canvasEl = document.getElementById('live-id-canvas');
const btnCapture = document.getElementById('btn-capture-live-id');
const btnRetry = document.getElementById('btn-retry');
const tickEl = document.getElementById('live-id-tick');
const resultPanel = document.getElementById('result-panel');
const spinner = document.getElementById('loading-spinner');

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

// Perform full Live Verify (OCR + Face Detection + Face Matching)
// This calls the /api/v1/live_verify endpoint which runs the complete
// Step 4.1 pipeline: document warp → PaddleOCR → face extraction → ArcFace.
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

    try {
        // Use /api/v1/live_verify — the FULL pipeline endpoint that does
        // document detection, OCR extraction, face detection, and face matching.
        const resp = await fetch(`${API_BASE}/api/v1/live_verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: dataUrl }),
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

    // --- Section 1: Face & Liveness Detection ---
    const holderDetected = !!data.holder_face_image_url;
    const idFaceDetected = !!data.id_card_face_image_url;

    const faceStatus = holderDetected
        ? '<span class="badge badge-success">LIVE PERSON DETECTED</span>'
        : '<span class="badge badge-danger">NO PERSON DETECTED</span>';

    html += `<h4>Face & Liveness Detection</h4>`;
    html += `<p>${faceStatus}</p>`;

    if (idFaceDetected) {
        html += `<p>ID Card Photo: <span class="badge badge-success">DETECTED</span></p>`;
    } else {
        html += `<p>ID Card Photo: <span class="badge badge-danger">NOT FOUND</span></p>`;
    }

    // Face images
    const hasImages = holderDetected || idFaceDetected || data.processed_image_url;
    if (hasImages) {
        html += `<div class="face-images">`;
        if (data.holder_face_image_url) {
            html += `<div><img src="${API_BASE}${data.holder_face_image_url}" alt="Holder Face"><br><small>Holder Face</small></div>`;
        }
        if (data.id_card_face_image_url) {
            html += `<div><img src="${API_BASE}${data.id_card_face_image_url}" alt="ID Card Face"><br><small>ID Card Face</small></div>`;
        }
        if (data.processed_image_url) {
            html += `<div><img src="${API_BASE}${data.processed_image_url}" alt="Processed Doc"><br><small>Processed Document</small></div>`;
        }
        html += `</div>`;
    }

    // Face match results (ArcFace)
    if (data.face_match_live_vs_id) {
        const fm = data.face_match_live_vs_id;
        const matchBadge = fm.verified
            ? '<span class="badge badge-success">MATCH</span>'
            : '<span class="badge badge-danger">NO MATCH</span>';
        html += `<p style="margin-top:12px;">Holder ↔ ID Card Face: ${matchBadge}`;
        if (fm.distance != null) {
            html += ` <small style="color:#888;">(distance: ${fm.distance.toFixed(3)}, threshold: ${fm.threshold.toFixed(3)})</small>`;
        }
        html += `</p>`;
    }

    html += `<hr style="margin: 20px 0; border: 0; border-top: 1px solid rgba(0,0,0,0.1);">`;

    // --- Section 2: OCR Extraction ---
    html += `<h4>OCR Extraction</h4>`;
    if (data.parsed_fields && Object.keys(data.parsed_fields).length > 0) {
        const fields = data.parsed_fields;

        if (fields.name) html += `<p><strong>Name:</strong> ${fields.name}</p>`;
        if (fields.dob) html += `<p><strong>DOB:</strong> ${fields.dob}</p>`;
        if (fields.gender) html += `<p><strong>Gender:</strong> ${fields.gender}</p>`;

        const idNum = fields.aadhaar_number || fields.pan_number || fields.id_number || fields.dl_number;
        if (idNum) html += `<p><strong>ID Number:</strong> ${idNum}</p>`;

        if (fields.father_name) html += `<p><strong>Father's Name:</strong> ${fields.father_name}</p>`;
        if (fields.address) html += `<p><strong>Address:</strong> ${fields.address}</p>`;

        // Show any remaining fields not already printed
        const shown = new Set(['name','dob','gender','aadhaar_number','pan_number','id_number','dl_number','father_name','address']);
        for (const [key, val] of Object.entries(fields)) {
            if (!shown.has(key) && val) {
                html += `<p><strong>${key.replace(/_/g, ' ')}:</strong> ${val}</p>`;
            }
        }
    } else {
        html += `<p class="text-muted">No ID card detected or OCR could not extract fields. Make sure the ID card is clearly visible.</p>`;
    }

    if (data.raw_text && data.raw_text.length > 0) {
        html += `<details style="margin-top: 12px;"><summary style="cursor:pointer;color:#888;font-size:0.85rem;">Raw OCR Text</summary>`;
        html += `<p style="margin-top: 8px; font-size: 0.8rem; color: #666; white-space: pre-wrap;">${data.raw_text.join('\n')}</p>`;
        html += `</details>`;
    }

    // --- Section 3: Document Detection Quality ---
    html += `<hr style="margin: 20px 0; border: 0; border-top: 1px solid rgba(0,0,0,0.1);">`;
    html += `<h4>Quality & Document Detection</h4>`;
    html += `<p><strong>Document Detected:</strong> ${data.document_detected ? '✅ Yes' : '❌ No'}</p>`;

    if (data.quality) {
        const q = data.quality;
        html += `<p><strong>Sharpness:</strong> ${q.sharp_ok ? '✅' : '❌'} ${q.sharpness != null ? `(${q.sharpness.toFixed(1)})` : ''}</p>`;
        html += `<p><strong>Lighting:</strong> ${q.lighting_ok ? '✅' : '❌'} ${q.brightness != null ? `(brightness: ${q.brightness.toFixed(1)})` : ''}</p>`;
    }

    if (data.step41_missing && data.step41_missing.length > 0) {
        html += `<p style="color:#f59e0b;"><strong>⚠ Missing:</strong> ${data.step41_missing.join(', ')}</p>`;
    }

    // Overall status
    html += `<hr style="margin: 20px 0; border: 0; border-top: 1px solid rgba(0,0,0,0.1);">`;
    const overallBadge = data.step41_complete
        ? '<span class="badge badge-success">STEP 4.1 COMPLETE</span>'
        : '<span class="badge badge-danger">STEP 4.1 INCOMPLETE</span>';
    html += `<p style="font-size: 1.1rem; font-weight: bold;">Overall: ${overallBadge}</p>`;

    resultPanel.innerHTML = html;
    resultPanel.classList.remove('hidden');
}

btnCapture.addEventListener('click', captureAndVerifyLiveId);
btnRetry.addEventListener('click', () => {
    tickEl.classList.add('hidden');
    resultPanel.classList.add('hidden');
    btnRetry.classList.add('hidden');
    btnCapture.disabled = false;
});

// Init
window.addEventListener('load', startCamera);
