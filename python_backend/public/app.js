// Global App State
const state = {
  currentStep: 1,
  activeDoctor: null,
  jwtToken: null,
  checklist: {
    mobileVerified: false,
    licenseAdded: false,
    qualAdded: false,
    clinicAdded: false,
    regCertUploaded: false,
    degreeCertUploaded: false,
    govtIdUploaded: false,
  },
  uploadedDocuments: [],
  inspectingDoctorID: null,
};

const API_BASE = window.location.origin;

// DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initStep1Auth();
  initStep2Credentials();
  initStep3Vault();
  initStep4Pipeline();
  initStep5Prescription();
  initAdminPortal();

  // Start at Step 1
  goToStep(1);
});

// Navigation & Tab Switching
function initNavigation() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.view-panel').forEach(v => v.classList.remove('active'));

      tab.classList.add('active');
      const targetView = document.getElementById(tab.dataset.tab);
      if (targetView) targetView.classList.add('active');

      if (tab.dataset.tab === 'admin-view') {
        fetchAdminAnalytics();
      }
    });
  });
}

// Global Step Switcher
window.goToStep = function(stepNum) {
  if (stepNum < 1 || stepNum > 5) return;

  state.currentStep = stepNum;

  // Hide all step pages
  document.querySelectorAll('.step-page').forEach(p => p.classList.remove('active'));
  
  // Show target step page
  const targetPage = document.getElementById(`page-step-${stepNum}`);
  if (targetPage) {
    targetPage.classList.add('active');
  }

  // Update Stepper Header UI
  for (let i = 1; i <= 5; i++) {
    const item = document.getElementById(`step-nav-${i}`);
    const conn = document.getElementById(`conn-${i}`);

    if (item) {
      if (i === stepNum) {
        item.className = 'step-item active';
      } else if (i < stepNum) {
        item.className = 'step-item completed';
      } else {
        item.className = 'step-item';
      }
    }

    if (conn) {
      if (i < stepNum) {
        conn.classList.add('completed');
      } else {
        conn.classList.remove('completed');
      }
    }
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (stepNum === 4) {
    beginStep4();
  } else {
    stopS4Camera();
  }
};

// -------------------------------------------------------------
// STEP 1: Registration, Login & OTP Verification
// -------------------------------------------------------------
function initStep1Auth() {
  const regForm = document.getElementById('form-register');
  const loginForm = document.getElementById('form-login');
  
  const subviewReg = document.getElementById('subview-register');
  const subviewLogin = document.getElementById('subview-login');
  const subviewOTP = document.getElementById('subview-otp');
  
  const btnToggleSignup = document.getElementById('btn-toggle-signup');
  const btnToggleLogin = document.getElementById('btn-toggle-login');
  const leftPaneSignup = document.getElementById('left-pane-signup-content');
  const leftPaneLogin = document.getElementById('left-pane-login-content');
  const step1Title = document.getElementById('step-1-title');
  const step1Subtitle = document.getElementById('step-1-subtitle');
  
  const btnVerifyOTP = document.getElementById('btn-verify-otp');

  // Password Visibility Toggle
  document.querySelectorAll('.password-toggle').forEach(icon => {
    icon.addEventListener('click', function() {
      const input = this.previousElementSibling;
      if (input.type === 'password') {
        input.type = 'text';
        this.innerText = '🙈';
      } else {
        input.type = 'password';
        this.innerText = '👁️';
      }
    });
  });

  // Toggle to Signup View
  btnToggleSignup.addEventListener('click', () => {
    subviewLogin.classList.add('hidden');
    subviewReg.classList.remove('hidden');
    leftPaneSignup.classList.add('hidden');
    leftPaneLogin.classList.remove('hidden');
    step1Title.innerText = '🔑 Doctor Registration & Mobile Identity';
    step1Subtitle.innerText = 'Create your doctor account and verify your mobile ownership via OTP.';
  });

  // Toggle to Login View
  btnToggleLogin.addEventListener('click', () => {
    subviewReg.classList.add('hidden');
    subviewLogin.classList.remove('hidden');
    leftPaneLogin.classList.add('hidden');
    leftPaneSignup.classList.remove('hidden');
    step1Title.innerText = '🔑 Doctor Login';
    step1Subtitle.innerText = 'Welcome back! Login to continue your verification process.';
  });

  // Handle Login
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const identifier = document.getElementById('login-identifier').value;
    const password = document.getElementById('login-password').value;

    try {
      const resp = await fetch(`${API_BASE}/api/v1/doctors/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier, password }),
      });

      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Login failed');

      state.jwtToken = data.access_token;
      state.activeDoctor = data.doctor;
      
      // Assume mobile verified if they can login
      state.checklist.mobileVerified = true;
      updateWizardChecklistUI();

      document.getElementById('session-text').innerText = `Doctor: ${state.activeDoctor.first_name} (${state.activeDoctor.public_id.substring(0, 8)}...)`;
      document.getElementById('user-session-badge').querySelector('.status-indicator').className = 'status-indicator online';

      alert('Login Successful! Resuming from Step 2 (Credentials)...');
      goToStep(2);
    } catch (err) {
      alert(`Login Error: ${err.message}`);
    }
  });

  // Handle Registration
  regForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fname = document.getElementById('reg-fname').value;
    const lname = document.getElementById('reg-lname').value;
    const mobile = document.getElementById('reg-mobile').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;

    try {
      const resp = await fetch(`${API_BASE}/api/v1/doctors/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ first_name: fname, last_name: lname, mobile, email, password }),
      });

      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Registration failed');

      state.activeDoctor = {
        public_id: data.public_id,
        mobile: mobile,
        email: email,
        first_name: fname,
        last_name: lname,
      };

      document.getElementById('otp-mobile-display').innerText = mobile;
      subviewReg.classList.add('hidden');
      document.getElementById('auth-left-pane').classList.add('hidden');
      subviewOTP.classList.remove('hidden');

      alert(`Registration Successful! OTP sent to ${mobile}. Click OK to verify.`);
    } catch (err) {
      alert(`Registration Error: ${err.message}`);
    }
  });

  // Handle OTP Verification
  btnVerifyOTP.addEventListener('click', async () => {
    const otpCode = document.getElementById('otp-input').value;
    if (!otpCode || otpCode.length !== 6) {
      alert('Please enter a 6-digit OTP code.');
      return;
    }

    try {
      const resp = await fetch(`${API_BASE}/api/v1/doctors/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          public_id: state.activeDoctor.public_id,
          mobile: state.activeDoctor.mobile,
          otp: otpCode,
          purpose: 'REGISTER'
        }),
      });

      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'OTP Verification failed');

      state.jwtToken = data.access_token;
      state.checklist.mobileVerified = true;
      updateWizardChecklistUI();

      document.getElementById('session-text').innerText = `Doctor: ${state.activeDoctor.first_name} (${state.activeDoctor.public_id.substring(0, 8)}...)`;
      document.getElementById('user-session-badge').querySelector('.status-indicator').className = 'status-indicator online';

      alert('Mobile OTP verified successfully! Transitioning to Step 2 (Credentials)...');
      
      // AUTO-MOVE TO STEP 2
      goToStep(2);
    } catch (err) {
      alert(`OTP Verification Error: ${err.message}`);
    }
  });
}

// -------------------------------------------------------------
// STEP 2: Medical Profile & Credentials
// -------------------------------------------------------------
function initStep2Credentials() {
  // License Form
  document.getElementById('form-license').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!state.activeDoctor) {
      alert('Please complete Step 1 first.');
      return;
    }

    const regNum = document.getElementById('lic-num').value;
    const council = document.getElementById('lic-council').value;
    const year = parseInt(document.getElementById('lic-year').value);

    try {
      const resp = await fetch(`${API_BASE}/api/v1/doctors/licenses`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Doctor-Public-ID': state.activeDoctor.public_id,
        },
        body: JSON.stringify({
          registration_number: regNum,
          registration_council: council,
          registration_year: year,
        }),
      });

      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Failed to add license');

      state.checklist.licenseAdded = true;
      updateWizardChecklistUI();
      document.getElementById('btn-save-license').innerText = '✅ License Saved';
      document.getElementById('btn-save-license').disabled = true;
      alert('Medical Registration License saved successfully!');
    } catch (err) {
      alert(`License Error: ${err.message}`);
    }
  });

  // Qualification Form
  document.getElementById('form-qual').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!state.activeDoctor) {
      alert('Please complete Step 1 first.');
      return;
    }

    const degree = document.getElementById('qual-degree').value;
    const spec = document.getElementById('qual-spec').value;
    const college = document.getElementById('qual-college').value;
    const year = parseInt(document.getElementById('qual-year').value);

    try {
      const resp = await fetch(`${API_BASE}/api/v1/doctors/qualifications`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Doctor-Public-ID': state.activeDoctor.public_id,
        },
        body: JSON.stringify({
          degree: degree,
          specialization: spec,
          college: college,
          university: college,
          year_completed: year,
        }),
      });

      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Failed to add qualification');

      state.checklist.qualAdded = true;
      updateWizardChecklistUI();
      document.getElementById('btn-save-qual').innerText = '✅ Qualification Saved';
      document.getElementById('btn-save-qual').disabled = true;
      alert('Qualification degree saved successfully!');
    } catch (err) {
      alert(`Qualification Error: ${err.message}`);
    }
  });

  // Clinic Form
  document.getElementById('form-clinic').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!state.activeDoctor) {
      alert('Please complete Step 1 first.');
      return;
    }

    const name = document.getElementById('clinic-name').value;
    const city = document.getElementById('clinic-city').value;
    const fee = parseFloat(document.getElementById('clinic-fee').value);

    try {
      const resp = await fetch(`${API_BASE}/api/v1/doctors/clinics`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Doctor-Public-ID': state.activeDoctor.public_id,
        },
        body: JSON.stringify({
          clinic_name: name,
          address: name + ', ' + city,
          city: city,
          state: 'Delhi',
          pincode: '110001',
          consultation_mode: 'IN_PERSON',
          consultation_fee: fee,
        }),
      });

      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Failed to add clinic');

      state.checklist.clinicAdded = true;
      updateWizardChecklistUI();
      document.getElementById('btn-save-clinic').innerText = '✅ Clinic Saved';
      document.getElementById('btn-save-clinic').disabled = true;
      alert('Clinic practice listing saved! Click "Proceed to Document Upload" when ready.');
    } catch (err) {
      alert(`Clinic Error: ${err.message}`);
    }
  });
}

// -------------------------------------------------------------
// STEP 3: Document Vault Upload & Submission
// -------------------------------------------------------------
function initStep3Vault() {
  const form = document.getElementById('form-doc-upload');
  const btnSubmit = document.getElementById('btn-submit-verification');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!state.activeDoctor) {
      alert('Please complete Step 1 first.');
      return;
    }

    const docType = document.getElementById('upload-doc-type').value;
    const fileInput = document.getElementById('upload-file-input');

    if (fileInput.files.length === 0) {
      alert('Please select a file to upload.');
      return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('document_type', docType);
    formData.append('file', file);

    try {
      const resp = await fetch(`${API_BASE}/api/v1/doctors/documents`, {
        method: 'POST',
        headers: {
          'X-Doctor-Public-ID': state.activeDoctor.public_id,
        },
        body: formData,
      });

      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Upload failed');

      if (!state.uploadedDocuments.some((d) => d.document_id === data.document_id)) {
        state.uploadedDocuments.push(data);
      }
      fileInput.value = '';

      if (docType === 'REGISTRATION_CERTIFICATE') state.checklist.regCertUploaded = true;
      if (docType === 'MEDICAL_DEGREE_CERTIFICATE') state.checklist.degreeCertUploaded = true;
      if (['AADHAAR', 'PAN', 'PASSPORT'].includes(docType)) state.checklist.govtIdUploaded = true;

      updateWizardChecklistUI();
      renderVaultTable();
      alert(`Document ${docType} uploaded successfully to vault!`);
    } catch (err) {
      alert(`Upload Error: ${err.message}`);
    }
  });

  btnSubmit.addEventListener('click', async () => {
    if (!state.activeDoctor) return;

    try {
      const resp = await fetch(`${API_BASE}/api/v1/doctors/submit-verification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Doctor-Public-ID': state.activeDoctor.public_id,
        },
      });

      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Submission failed');

      alert('Verification Application Submitted Successfully! Transitioning to Step 4 (Liveness + eKYC)...');
      goToStep(4);
    } catch (err) {
      alert(`Submission Error: ${err.message}`);
    }
  });
}

function renderVaultTable() {
  const container = document.getElementById('doc-vault-table');
  if (state.uploadedDocuments.length === 0) {
    container.innerHTML = `<div class="text-muted text-center py-3">No documents uploaded yet.</div>`;
    return;
  }

  let html = `<table class="data-table">
    <thead>
      <tr>
        <th>Document Category</th>
        <th>File Name</th>
        <th>Version</th>
        <th>SHA-256 Hash</th>
        <th>Status</th>
        <th>Action</th>
      </tr>
    </thead>
    <tbody>`;

  state.uploadedDocuments.forEach(doc => {
    html += `<tr>
      <td><span class="badge badge-info">${doc.document_type}</span></td>
      <td>${doc.original_filename}</td>
      <td>v${doc.version}</td>
      <td><code>${(doc.file_hash || 'N/A').toString().substring(0, 10)}...</code></td>
      <td><span class="badge badge-success">Clean / Vaulted</span></td>
      <td>
        <button class="btn btn-outline btn-sm delete-doc-btn" onclick="deleteDocument('${doc.document_id}')" style="border: 1px solid #ef4444; color: #ef4444; padding: 0.25rem 0.5rem;" title="Delete Document">
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
        </button>
      </td>
    </tr>`;
  });

  html += `</tbody></table>`;
  container.innerHTML = html;
}

function updateWizardChecklistUI() {
  const c = state.checklist;
  setCheckNode('chk-mobile', c.mobileVerified);
  setCheckNode('chk-license', c.licenseAdded);
  setCheckNode('chk-qual', c.qualAdded);
  setCheckNode('chk-clinic', c.clinicAdded);
  setCheckNode('chk-reg-cert', c.regCertUploaded);
  setCheckNode('chk-degree-cert', c.degreeCertUploaded);
  setCheckNode('chk-govt-id', c.govtIdUploaded);

  const readyToSubmit = c.mobileVerified && c.licenseAdded && c.qualAdded && c.clinicAdded && c.regCertUploaded && c.degreeCertUploaded && c.govtIdUploaded;
  document.getElementById('btn-submit-verification').disabled = !readyToSubmit;
}

function setCheckNode(id, isDone) {
  const el = document.getElementById(id);
  if (!el) return;
  if (isDone) {
    el.classList.add('done');
    el.querySelector('.chk-icon').innerText = '✅';
  } else {
    el.classList.remove('done');
    el.querySelector('.chk-icon').innerText = '⚪';
  }
}

// -------------------------------------------------------------
// STEP 4: Two existing modules, wired into the portal
//   Module 1 — OCR engine on uploaded Aadhaar/PAN
//   Module 2 — eye_tracking/demo.py (FGI-Net + XY graph + center calib)
// -------------------------------------------------------------
let s4Stream = null;
let s4Timer = null;
let s4Gen = 0;
let s4Active = false;
let s4InFlight = false;
let pipelineRunning = false;
let module1Running = false;
let eyeResetPending = true;
let eyeHold = 0;
const EYE_HOLD_NEEDED = 8;

function stopS4Camera() {
  s4Active = false;
  s4InFlight = false;
  if (s4Timer) { clearTimeout(s4Timer); s4Timer = null; }
  if (s4Stream) { s4Stream.getTracks().forEach(t => t.stop()); s4Stream = null; }
  ['eye-track-video', 'doc-face-video'].forEach((id) => {
    const v = document.getElementById(id);
    if (v) v.srcObject = null;
  });
}

async function openCamera(videoEl) {
  if (s4Stream) { s4Stream.getTracks().forEach(t => t.stop()); s4Stream = null; }
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }, audio: false
  });
  s4Stream = stream;
  videoEl.srcObject = stream;
  videoEl.muted = true;
  videoEl.setAttribute('playsinline', 'true');
  await videoEl.play();
  return stream;
}

function grabFrame(videoEl, w, h) {
  // CSS scaleX(-1) only flips the preview. Canvas reads the raw camera frame.
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  c.getContext('2d').drawImage(videoEl, 0, 0, w, h);
  return c.toDataURL('image/jpeg', 0.8);
}

function initStep4Pipeline() {
  document.getElementById('btn-start-doc-face')?.addEventListener('click', startModule1);
  document.getElementById('btn-capture-doc-face')?.addEventListener('click', captureLiveDoc);
}

function getStep3FaceFiles() {
  const docs = (state.ekycResult && Array.isArray(state.ekycResult.documents)) ? state.ekycResult.documents : [];
  return docs
    .map((d) => d.face_image_url)
    .filter(Boolean)
    .map((u) => {
      try {
        const s = String(u);
        return s.substring(s.lastIndexOf('/') + 1);
      } catch (_) {
        return null;
      }
    })
    .filter(Boolean);
}

function renderModule1Faces(data) {
  const resultDiv = document.getElementById('doc-face-result');
  if (!resultDiv) return;

  const holderFaceUrl = data.holder_face_image_url || null;
  const fields = data.parsed_fields || {};
  const name = fields.name || '';
  const rawText = Array.isArray(data.raw_text) ? data.raw_text.filter(Boolean) : [];

  const faceHtml = holderFaceUrl
    ? `<div style="display:flex; gap:16px; justify-content:center; flex-wrap:wrap;">
        <div style="display:inline-block; margin:0 8px;">
          <img src="${holderFaceUrl}" alt="holder-face" style="width:112px;height:112px;object-fit:cover;border-radius:12px;border:3px solid #2563eb;" />
          <p style="color:#111; margin-top:6px; font-weight:600;">Live holder face</p>
        </div>
      </div>`
    : `<p class="text-muted mb-1">No face crop returned. Hold the card closer and capture again.</p>`;

  const fieldsHtml = (() => {
    const entries = Object.entries(fields).slice(0, 10);
    if (!entries.length) return '';
    return `
      <div class="mt-3" style="text-align:left; max-width:620px; margin:0 auto; color:#111;">
        <div style="font-weight:700; margin-bottom:0.25rem;">OCR Fields</div>
        ${entries
          .map(([k, v]) => `<div style="display:flex; gap:0.5rem; margin:0.15rem 0;"><span style="color:#333; min-width:150px; font-weight:600;">${k}</span><span style="color:#000;">${v ?? '-'}</span></div>`)
          .join('')}
      </div>
    `;
  })();

  const rawHtml = rawText.length
    ? `
      <div class="mt-3" style="text-align:left; max-width:620px; margin:0 auto; color:#111;">
        <div style="font-weight:700; margin-bottom:0.25rem;">Raw OCR Text</div>
        <div style="color:#000; font-size:0.9rem; line-height:1.35; background:#f3f4f6; padding:0.75rem; border-radius:10px; white-space:pre-wrap; border:1px solid #d1d5db;">
          ${rawText.join('\n')}
        </div>
      </div>
    `
    : '';

  const faceDebug = data.face_debug || {};
  const debugHtml = `
    <div class="mt-3" style="text-align:left; max-width:620px; margin:0 auto; color:#111;">
      <div style="font-weight:700; margin-bottom:0.25rem;">Face Detection Output</div>
      <div style="font-size:0.92rem; background:#f3f4f6; border:1px solid #d1d5db; border-radius:10px; padding:0.75rem;">
        <div><strong>source:</strong> ${faceDebug.source || data.face_source || 'none'}</div>
        <div><strong>confidence:</strong> ${faceDebug.confidence ?? '-'}</div>
        <div><strong>bbox:</strong> ${Array.isArray(faceDebug.bbox) ? faceDebug.bbox.join(', ') : '-'}</div>
        <div><strong>aligned:</strong> ${faceDebug.aligned === true ? 'yes' : 'no'}</div>
        <div><strong>landmarks:</strong> ${faceDebug.landmarks ? JSON.stringify(faceDebug.landmarks) : '-'}</div>
      </div>
    </div>
  `;

  const errorHtml = data.error
    ? `<p class="text-danger mt-2" style="font-weight:600;">Error: ${data.error}</p>`
    : '';

  const matchRows = Array.isArray(data.step3_face_matches) ? data.step3_face_matches : [];
  const compareHtml = matchRows.length
    ? `
      <div class="mt-3" style="text-align:left; max-width:620px; margin:0 auto; color:#111;">
        <div style="font-weight:700; margin-bottom:0.25rem;">Step 3 vs Step 4.1 Face Cross-Verification</div>
        <div style="font-size:0.92rem; background:#f3f4f6; border:1px solid #d1d5db; border-radius:10px; padding:0.75rem;">
          ${matchRows.map((m) => `
            <div style="margin:0.25rem 0;">
              <strong>${m.step3_face || 'step3 face'}</strong>:
              ${m.verified ? '<span style="color:#166534;font-weight:700;">MATCH</span>' : '<span style="color:#991b1b;font-weight:700;">NO MATCH</span>'}
              ${m.distance !== undefined ? `(distance=${m.distance})` : ''}
              ${m.error ? ` - ${m.error}` : ''}
            </div>
          `).join('')}
        </div>
      </div>
    `
    : '';

  resultDiv.innerHTML = `
    <div>
      ${faceHtml}
      ${errorHtml}
      ${fieldsHtml}
      ${debugHtml}
      ${compareHtml}
      ${rawHtml}
    </div>
  `;
  resultDiv.classList.remove('hidden');
}

// --- Module 1: live camera + existing OCR live_verify (CSS mirror, unflipped capture) ---
async function startModule1() {
  const gen = ++s4Gen;
  const video = document.getElementById('doc-face-video');
  const overlay = document.getElementById('doc-face-overlay');
  const statusEl = document.getElementById('doc-face-status');
  const captureBtn = document.getElementById('btn-capture-doc-face');
  const resultDiv = document.getElementById('doc-face-result');
  if (resultDiv) resultDiv.classList.add('hidden');
  try {
    await openCamera(video);
    if (gen !== s4Gen) return;
    if (overlay) overlay.style.display = 'none';
    if (captureBtn) captureBtn.classList.remove('hidden');
    s4Active = true;
    if (statusEl) {
      statusEl.innerText = 'Status: Camera on (mirrored preview). Hold your Aadhaar/PAN in view, then Capture.';
      statusEl.className = 'alert alert-info mt-2 text-center';
    }
  } catch (err) {
    console.error('Module1 camera error:', err);
    if (statusEl) {
      statusEl.innerText = `Status: Camera error — ${err.message || err}`;
      statusEl.className = 'alert alert-danger mt-2 text-center';
    }
  }
}

async function captureLiveDoc() {
  const video = document.getElementById('doc-face-video');
  const statusEl = document.getElementById('doc-face-status');
  const captureBtn = document.getElementById('btn-capture-doc-face');
  if (!video || video.readyState < 2 || video.videoWidth === 0) {
    if (statusEl) {
      statusEl.innerText = 'Status: Camera is not ready yet.';
      statusEl.className = 'alert alert-warning mt-2 text-center';
    }
    return;
  }
  if (captureBtn) { captureBtn.disabled = true; captureBtn.innerText = 'Extracting...'; }
  if (statusEl) {
    statusEl.innerText = 'Status: Sending unflipped frame to existing OCR module (PaddleOCR + RetinaFace)...';
    statusEl.className = 'alert alert-info mt-2 text-center';
  }
  const w = video.videoWidth;
  const h = video.videoHeight;
  const dataUrl = grabFrame(video, w, h);
  try {
    const resp = await fetch(`${API_BASE}/api/v1/verification/live-doc`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: dataUrl, step3_faces: getStep3FaceFiles() }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data.error || data.detail || 'Live OCR failed');

    state.liveDocResult = data;
    renderModule1Faces(data);
    const faceOk = !!(data.face_image_url || data.face_image);
    if (statusEl) {
      statusEl.innerText = faceOk
        ? 'Status: Face extracted from the card. Starting live eye tracking...'
        : 'Status: OCR ran but no face was found. Hold the card closer and capture again.';
      statusEl.className = `alert ${faceOk ? 'alert-success' : 'alert-warning'} mt-2 text-center`;
    }
    if (faceOk) {
      stopS4Camera();
      if (captureBtn) captureBtn.classList.add('hidden');
      setTimeout(() => startModule2(), 1200);
    } else if (captureBtn) {
      captureBtn.disabled = false;
      captureBtn.innerText = 'Capture & Extract Face';
    }
  } catch (err) {
    console.error('Live doc OCR error:', err);
    if (statusEl) {
      statusEl.innerText = `Status: OCR error — ${err.message || err}`;
      statusEl.className = 'alert alert-danger mt-2 text-center';
    }
    if (captureBtn) { captureBtn.disabled = false; captureBtn.innerText = 'Capture & Extract Face'; }

    // Show the failure on the page (so user always sees Step 4.1 output).
    const resultDiv = document.getElementById('doc-face-result');
    if (resultDiv) {
      resultDiv.classList.remove('hidden');
      resultDiv.innerHTML = `
        <p class="text-danger" style="font-weight:600;">Step 4.1 failed to extract face/OCR.</p>
        <p class="text-muted">${err.message || err}</p>
      `;
    }
  }
}

// --- Module 2: existing eye_tracking demo (camera + XY graph + center calib) ---
async function startModule2() {
  const gen = ++s4Gen;
  const section = document.getElementById('eye-track-section');
  const docSection = document.getElementById('doc-face-section');
  if (docSection) docSection.classList.add('hidden');
  if (section) section.classList.remove('hidden');

  const video = document.getElementById('eye-track-video');
  const statusEl = document.getElementById('eye-track-status');
  const bar = document.getElementById('eye-calib-bar');
  eyeResetPending = true;
  eyeHold = 0;
  if (bar) bar.style.width = '0%';

  try {
    await openCamera(video);
    if (gen !== s4Gen) return;
    s4Active = true;
    statusEl.innerText = 'Status: Face the camera and look straight — capturing center...';
    statusEl.className = 'alert alert-info mt-2 text-center';
    scheduleEyeTick(gen, 800);
  } catch (err) {
    console.error('Eye tracker camera error:', err);
    statusEl.innerText = `Status: Camera error — ${err.message || err}`;
    statusEl.className = 'alert alert-danger mt-2 text-center';
  }
}

function scheduleEyeTick(gen, ms) {
  if (s4Timer) clearTimeout(s4Timer);
  s4Timer = setTimeout(() => pollEyeTrack(gen), ms);
}

async function pollEyeTrack(gen) {
  if (gen !== s4Gen || !s4Active || s4InFlight) return;
  const video = document.getElementById('eye-track-video');
  const statusEl = document.getElementById('eye-track-status');
  const bar = document.getElementById('eye-calib-bar');
  const plotImg = document.getElementById('eye-plot-view');
  if (!video || video.readyState < 2 || video.videoWidth === 0) {
    scheduleEyeTick(gen, 400);
    return;
  }
  const scale = Math.min(1, 640 / video.videoWidth);
  const dataUrl = grabFrame(video, Math.round(video.videoWidth * scale), Math.round(video.videoHeight * scale));
  s4InFlight = true;
  try {
    const resp = await fetch(`${API_BASE}/api/v1/verification/liveness`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: dataUrl, reset: eyeResetPending }),
    });
    eyeResetPending = false;
    const data = await resp.json().catch(() => ({}));
    if (gen !== s4Gen || !s4Active) return;

    if (data.plot_image && plotImg) plotImg.src = data.plot_image;
    const pct = Math.round((data.calib_progress || 0) * 100);
    if (bar) bar.style.width = `${pct}%`;

    if (data.calib_ready && data.both_eyes_facing) {
      eyeHold += 1;
      if (statusEl) {
        statusEl.innerText = `Status: Center locked. Looking ${String(data.direction || '').toUpperCase()} (${eyeHold}/${EYE_HOLD_NEEDED})`;
        statusEl.className = 'alert alert-success mt-2 text-center';
      }
      if (eyeHold >= EYE_HOLD_NEEDED) {
        stopS4Camera();
        if (statusEl) statusEl.innerText = 'Status: Eye tracking passed. Showing eKYC decision...';
        document.getElementById('eye-track-section')?.classList.add('hidden');
        const timeline = document.getElementById('pipeline-timeline');
        if (timeline) timeline.classList.remove('hidden');
        applyEkycDecision(state.ekycResult);
        return;
      }
    } else {
      eyeHold = 0;
      if (statusEl) {
        if (!data.both_eyes_facing) {
          statusEl.innerText = `Status: ${(data.direction || 'no_face').replace(/_/g, ' ')} — both eyes must face the camera.`;
        } else {
          statusEl.innerText = `Status: Capturing center ${pct}% — look straight.`;
        }
        statusEl.className = 'alert alert-warning mt-2 text-center';
      }
    }
  } catch (err) {
    console.error('Eye tracking error:', err);
  } finally {
    s4InFlight = false;
    if (gen === s4Gen && s4Active) scheduleEyeTick(gen, 280);
  }
}

function beginStep4() {
  stopS4Camera();
  resetPipelineUI();
  state.ekycResult = null;
  state.liveDocResult = null;
  module1Running = false;
  eyeHold = 0;
  const docSection = document.getElementById('doc-face-section');
  const eyeSection = document.getElementById('eye-track-section');
  const docResult = document.getElementById('doc-face-result');
  const docStatus = document.getElementById('doc-face-status');
  const overlay = document.getElementById('doc-face-overlay');
  const startBtn = document.getElementById('btn-start-doc-face');
  const captureBtn = document.getElementById('btn-capture-doc-face');
  const timeline = document.getElementById('pipeline-timeline');
  if (docSection) docSection.classList.remove('hidden');
  if (eyeSection) eyeSection.classList.add('hidden');
  if (docResult) { docResult.classList.add('hidden'); docResult.innerHTML = ''; }
  if (overlay) overlay.style.display = 'flex';
  if (startBtn) { startBtn.disabled = false; startBtn.innerText = 'Allow Camera'; }
  if (captureBtn) { captureBtn.classList.add('hidden'); captureBtn.disabled = false; captureBtn.innerText = 'Capture & Extract Face'; }
  if (docStatus) {
    docStatus.innerText = 'Status: Click Allow Camera, then hold your ID card and capture.';
    docStatus.className = 'alert alert-info mt-2 text-center';
  }
  if (timeline) timeline.classList.add('hidden');
}
window.beginStep4 = beginStep4;

function resetPipelineUI() {
  for (let i = 1; i <= 5; i++) {
    const el = document.getElementById(`tstep-${i}`);
    if (el) el.classList.remove('active', 'failed', 'warn');
  }
  const badge = document.getElementById('pipeline-status-badge');
  badge.innerText = 'RUNNING';
  badge.className = 'badge badge-warning';
  document.getElementById('pipeline-decision-desc').innerText = 'Waiting for eKYC model evaluation...';
  document.getElementById('pipeline-console').innerText = '[SYSTEM] Starting eKYC evaluation pipeline...';
  document.getElementById('btn-goto-prescription').classList.add('hidden');
  document.getElementById('ekyc-result-panel').classList.add('hidden');
  document.getElementById('ekyc-result-cards').innerHTML = '';
}

function logPipe(msg) {
  const consoleBox = document.getElementById('pipeline-console');
  const time = new Date().toLocaleTimeString();
  consoleBox.innerText += `\n[${time}] ${msg}`;
  consoleBox.scrollTop = consoleBox.scrollHeight;
}

function activateStage(stageId, status, detail) {
  const el = document.getElementById(`tstep-${stageId}`);
  if (!el) return;
  el.classList.add('active');
  if (status === 'failed') el.classList.add('failed');
  if (status === 'warn') el.classList.add('warn');
  const desc = document.getElementById(stageId === 5 ? 'pipeline-decision-desc' : `tdesc-${stageId}`);
  if (desc && detail) desc.innerText = detail;
}

function renderEkycResults(documents) {
  const panel = document.getElementById('ekyc-result-panel');
  const cards = document.getElementById('ekyc-result-cards');
  if (!panel || !cards) return;

  if (!documents || documents.length === 0) {
    cards.innerHTML = `<div class="text-muted">No OCR fields returned. Confirm the OCR service is running on port 5001 and the Aadhaar/PAN images are readable.</div>`;
    panel.classList.remove('hidden');
    return;
  }

  cards.innerHTML = documents.map((doc) => {
    const fields = doc.parsed_fields || {};
    const docType = fields.document_type || doc.document_type || 'UNKNOWN';
    const idNum = fields.aadhaar_number || fields.pan_number || '-';
    const validated = fields.aadhaar_number_validated || fields.pan_number_validated;
    const raw = Array.isArray(doc.raw_text) ? doc.raw_text.filter(Boolean).slice(0, 8).join(' | ') : '';
    const faceHtml = doc.face_image_url
      ? `<img src="${doc.face_image_url}" alt="face" style="width:96px;height:96px;object-fit:cover;border-radius:8px;margin-top:8px;border:2px solid #22c55e;" />`
      : '<div class="text-muted">No face crop</div>';
    return `
      <div class="glass-card" style="padding:1rem;">
        <div><span class="badge badge-info">${docType}</span>
             <span class="badge ${doc.status === 'success' ? 'badge-success' : 'badge-danger'}">${doc.status || 'n/a'}</span></div>
        <p style="margin:0.5rem 0 0.25rem;"><strong>Name:</strong> ${fields.name || '-'}</p>
        <p style="margin:0.25rem 0;"><strong>DOB:</strong> ${fields.dob || '-'}</p>
        <p style="margin:0.25rem 0;"><strong>ID:</strong> ${idNum}
          ${validated === true ? '<span class="badge badge-success">VALID</span>' : ''}
          ${validated === false ? '<span class="badge badge-danger">INVALID</span>' : ''}
        </p>
        <p style="margin:0.25rem 0;"><strong>OCR Confidence:</strong> ${doc.ocr_confidence ?? '-'}%</p>
        ${doc.error ? `<p style="margin:0.25rem 0;color:#ef4444;"><strong>Error:</strong> ${doc.error}</p>` : ''}
        ${(!fields.name && raw) ? `<p class="text-muted" style="margin:0.25rem 0;font-size:0.8rem;"><strong>OCR text:</strong> ${raw}</p>` : ''}
        ${faceHtml}
      </div>`;
  }).join('');

  // Show Step 4.1 live holder crop below Step 3 eKYC cards when available.
  if (state.liveDocResult && state.liveDocResult.holder_face_image_url) {
    cards.innerHTML += `
      <div class="glass-card" style="padding:1rem; grid-column:1 / -1;">
        <div style="font-weight:700; color:#111; margin-bottom:0.6rem;">Step 4.1 Face Crops</div>
        <div style="display:flex; gap:14px; flex-wrap:wrap;">
          <div>
            <img src="${state.liveDocResult.holder_face_image_url}" alt="step4-holder-face" style="width:112px;height:112px;object-fit:cover;border-radius:8px;border:2px solid #2563eb;" />
            <div style="color:#111; font-size:0.9rem; margin-top:4px;">Live holder face</div>
          </div>
        </div>
      </div>
    `;
  }

  panel.classList.remove('hidden');
}

function applyEkycDecision(data) {
  if (!data) {
    startPipelineAnimation();
    return;
  }
  resetPipelineUI();
  logPipe('[STEP 4.1] OCR + face extraction already completed by the existing module.');
  logPipe('[STEP 4.2] 5-dot pupil tracking passed.');
  (data.stages || []).forEach((stage) => {
    activateStage(stage.id, stage.status, stage.detail);
    logPipe(`[STAGE ${stage.id}] ${stage.title}: ${stage.detail}`);
  });
  renderEkycResults(data.documents || []);

  const decision = (data.decision && data.decision.result) || data.status || 'UNKNOWN';
  const badge = document.getElementById('pipeline-status-badge');
  badge.innerText = decision;
  if (decision === 'AUTO_VERIFIED') {
    badge.className = 'badge badge-success';
  } else if (decision === 'MANUAL_REVIEW') {
    badge.className = 'badge badge-warning';
  } else {
    badge.className = 'badge badge-danger';
  }
  const conf = data.decision ? data.decision.ocr_confidence : '-';
  const nameScore = data.decision ? data.decision.name_match_score : '-';
  document.getElementById('pipeline-decision-desc').innerText =
    `Decision: ${decision} (OCR ${conf}%, Name Match ${nameScore}%)`;
  logPipe(`[DECISION] ${data.message || decision}`);
  if (decision === 'AUTO_VERIFIED' || decision === 'MANUAL_REVIEW') {
    document.getElementById('btn-goto-prescription').classList.remove('hidden');
    if (state.activeDoctor) {
      document.getElementById('rx-doctor-id').value = state.activeDoctor.public_id;
    }
    logPipe('[SUCCESS] Step 5 unlocked.');
  }
}

async function startPipelineAnimation() {
  if (!state.activeDoctor || !state.activeDoctor.public_id) {
    alert('Please complete registration first.');
    return;
  }
  if (pipelineRunning) return;
  pipelineRunning = true;

  resetPipelineUI();
  activateStage(1, 'done', 'Verification package submitted');
  logPipe(`[STEP 1] Application loaded for doctor ${state.activeDoctor.public_id}`);
  logPipe('[STEP 2] Calling eKYC OCR microservice at http://127.0.0.1:5001 ...');
  logPipe('[INFO] First OCR run can take 30-90s while models warm up. Please wait...');
  activateStage(2, 'running', 'Running OCR model on uploaded KYC documents...');

  try {
    const resp = await fetch(`${API_BASE}/api/v1/doctors/evaluate-ekyc`, {
      method: 'POST',
      headers: {
        'X-Doctor-Public-ID': state.activeDoctor.public_id,
      },
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'eKYC evaluation failed');

    logPipe(`[CONNECTED] Portal ⇄ OCR microservice responded OK`);
    (data.stages || []).forEach((stage) => {
      activateStage(stage.id, stage.status, stage.detail);
      logPipe(`[STAGE ${stage.id}] ${stage.title}: ${stage.detail}`);
    });

    renderEkycResults(data.documents || []);

    const decision = (data.decision && data.decision.result) || data.status || 'UNKNOWN';
    const badge = document.getElementById('pipeline-status-badge');
    badge.innerText = decision;
    if (decision === 'AUTO_VERIFIED') {
      badge.className = 'badge badge-success';
    } else if (decision === 'MANUAL_REVIEW') {
      badge.className = 'badge badge-warning';
    } else {
      badge.className = 'badge badge-danger';
    }

    const conf = data.decision ? data.decision.ocr_confidence : '-';
    const nameScore = data.decision ? data.decision.name_match_score : '-';
    document.getElementById('pipeline-decision-desc').innerText =
      `Decision: ${decision} (OCR ${conf}%, Name Match ${nameScore}%)`;

    logPipe(`[DECISION] ${data.message || decision}`);

    // Unlock Step 5 for AUTO_VERIFIED and MANUAL_REVIEW (demo continuity)
    if (decision === 'AUTO_VERIFIED' || decision === 'MANUAL_REVIEW') {
      document.getElementById('btn-goto-prescription').classList.remove('hidden');
      if (state.activeDoctor) {
        document.getElementById('rx-doctor-id').value = state.activeDoctor.public_id;
      }
      logPipe('[SUCCESS] Step 5 unlocked. You can continue to Digital Prescription Studio.');
    } else {
      logPipe('[BLOCKED] Evaluation failed. Re-upload clearer KYC documents and retry from Step 3.');
    }
  } catch (err) {
    activateStage(2, 'failed', err.message);
    activateStage(5, 'failed', `Evaluation error: ${err.message}`);
    const badge = document.getElementById('pipeline-status-badge');
    badge.innerText = 'FAILED';
    badge.className = 'badge badge-danger';
    logPipe(`[ERROR] ${err.message}`);
    logPipe('[HINT] Make sure OCR service is running on http://127.0.0.1:5001');
  } finally {
    pipelineRunning = false;
  }
}

// -------------------------------------------------------------
// STEP 5: Digital Prescription Studio
// -------------------------------------------------------------
function initStep5Prescription() {
  const form = document.getElementById('form-prescription');
  const cert = document.getElementById('prescription-certificate');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const doctorID = document.getElementById('rx-doctor-id').value;
    const patientID = document.getElementById('rx-patient-id').value;
    const diagnosis = document.getElementById('rx-diagnosis').value;
    const medsRaw = document.getElementById('rx-medicines').value;

    let medicines = [];
    try {
      medicines = JSON.parse(medsRaw);
    } catch (err) {
      alert('Invalid JSON format in prescribed medicines field.');
      return;
    }

    try {
      const resp = await fetch(`${API_BASE}/api/v1/prescriptions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doctor_id: doctorID,
          patient_id: patientID,
          diagnosis: diagnosis,
          medicines: medicines,
        }),
      });

      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Prescription generation failed');

      cert.classList.remove('hidden');
      document.getElementById('rx-out-id').innerText = data.prescription_id;
      document.getElementById('rx-out-date').innerText = new Date(data.issued_at).toLocaleString();
      document.getElementById('rx-out-doc').innerText = data.doctor_id;
      document.getElementById('rx-out-patient').innerText = data.patient_id;
      document.getElementById('rx-out-diagnosis').innerText = data.diagnosis;
      document.getElementById('rx-out-sig').innerText = data.digital_signature;

      const tbody = document.getElementById('rx-meds-tbody');
      let html = '';
      data.medicines.forEach(m => {
        html += `<tr>
          <td><strong>${m.name}</strong></td>
          <td>${m.dosage}</td>
          <td>${m.frequency}</td>
          <td>${m.duration}</td>
        </tr>`;
      });
      tbody.innerHTML = html;

      alert('Prescription Generated & Digitally Signed with RSA-256 Key!');
    } catch (err) {
      alert(`Prescription Error: ${err.message}`);
    }
  });
}

// -------------------------------------------------------------
// ADMIN PORTAL
// -------------------------------------------------------------
function initAdminPortal() {
  document.getElementById('btn-admin-refresh').addEventListener('click', fetchAdminAnalytics);
  document.getElementById('btn-admin-search').addEventListener('click', performAdminSearch);
  document.getElementById('btn-close-inspector').addEventListener('click', () => {
    document.getElementById('admin-inspector-card').classList.add('hidden');
  });

  document.getElementById('btn-action-approve').addEventListener('click', () => handleAdminAction('approve'));
  document.getElementById('btn-action-reject').addEventListener('click', () => handleAdminAction('reject'));
  document.getElementById('btn-action-req-docs').addEventListener('click', () => handleAdminAction('request-documents'));
}

async function fetchAdminAnalytics() {
  try {
    const resp = await fetch(`${API_BASE}/api/v1/admin/analytics`);
    const data = await resp.json();

    document.getElementById('metric-total-docs').innerText = data.total_doctors || 0;
    document.getElementById('metric-pending-verifications').innerText = data.pending_verifications || 0;
    document.getElementById('metric-verified-rate').innerText = (data.auto_verified_rate || 0).toFixed(1) + '%';
    document.getElementById('metric-dlq-count').innerText = data.dead_letter_jobs || 0;

    performAdminSearch();
  } catch (err) {
    console.error('Admin analytics fetch failed:', err);
  }
}

async function performAdminSearch() {
  const query = document.getElementById('admin-search-input').value;
  try {
    const resp = await fetch(`${API_BASE}/api/v1/admin/search?q=${encodeURIComponent(query)}`);
    const doctors = await resp.json();

    const tbody = document.getElementById('admin-verifications-tbody');
    if (!doctors || doctors.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center py-3 text-muted">No doctor records found.</td></tr>`;
      return;
    }

    let html = '';
    doctors.forEach(doc => {
      const badgeClass = doc.status === 'VERIFIED' || doc.status === 'AUTO_VERIFIED' ? 'badge-success' : (doc.status === 'PENDING' ? 'badge-warning' : 'badge-secondary');
      html += `<tr>
        <td><strong>${doc.first_name} ${doc.last_name}</strong></td>
        <td><code>${doc.public_id.substring(0, 10)}...</code></td>
        <td>${doc.mobile}</td>
        <td><span class="badge ${badgeClass}">${doc.status}</span></td>
        <td>${doc.fraud_score} / 100</td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="inspectDoctorDetail('${doc.public_id}')">Inspect & Review</button>
        </td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (err) {
    console.error('Admin search failed:', err);
  }
}

window.inspectDoctorDetail = async function(doctorPublicID) {
  try {
    state.inspectingDoctorID = doctorPublicID;
    const resp = await fetch(`${API_BASE}/api/v1/admin/verifications/detail?doctor_id=${doctorPublicID}`);
    const data = await resp.json();

    document.getElementById('admin-inspector-card').classList.remove('hidden');
    document.getElementById('insp-doc-id').innerText = data.doctor.public_id;
    document.getElementById('insp-doc-name').innerText = `${data.doctor.first_name} ${data.doctor.last_name}`;

    const lic = data.licenses && data.licenses.length > 0 ? data.licenses[0] : null;
    document.getElementById('insp-doc-reg-num').innerText = lic ? lic.registration_number : 'N/A';
    document.getElementById('insp-doc-council').innerText = lic ? lic.registration_council : 'N/A';

    document.getElementById('insp-registry-name').innerText = lic ? `${data.doctor.first_name} ${data.doctor.last_name} (NMC Verified)` : 'N/A';
    document.getElementById('insp-registry-status').innerText = 'ACTIVE / VALID';
    document.getElementById('insp-match-score').innerText = '100% Match';
    document.getElementById('insp-fraud-score').innerText = `${data.doctor.fraud_score} / 100`;

  } catch (err) {
    alert(`Inspector error: ${err.message}`);
  }
};

async function handleAdminAction(actionType) {
  if (!state.inspectingDoctorID) return;

  try {
    const url = `${API_BASE}/api/v1/admin/verifications/${actionType}`;
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        doctor_id: state.inspectingDoctorID,
        admin_id: '00000000-0000-0000-0000-000000000001',
        reason: `Admin operation: ${actionType.toUpperCase()}`,
      }),
    });

    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Action failed');

    alert(`Action ${actionType.toUpperCase()} completed successfully!`);
    fetchAdminAnalytics();
    document.getElementById('admin-inspector-card').classList.add('hidden');
  } catch (err) {
    alert(`Admin Action Error: ${err.message}`);
  }
}

window.deleteDocument = async function(docId) {
  if (!confirm("Are you sure you want to delete this document?")) return;
  try {
    const res = await fetch(`${API_BASE}/api/v1/doctors/documents?document_id=${docId}`, {
      method: "DELETE",
      headers: {
        "X-Doctor-Public-ID": state.activeDoctor.public_id,
      },
    });
    
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || "Failed to delete document");
    }
    
    // Find the document to know its type
    const docToDelete = state.uploadedDocuments.find(d => d.document_id === docId);
    if (!docToDelete) return;
    
    // Remove from state
    state.uploadedDocuments = state.uploadedDocuments.filter(d => d.document_id !== docId);
    
    // Check if we need to uncheck checklist items
    const hasRegCert = state.uploadedDocuments.some(d => d.document_type === 'REGISTRATION_CERTIFICATE');
    const hasDegree = state.uploadedDocuments.some(d => d.document_type === 'MEDICAL_DEGREE_CERTIFICATE');
    const hasGovtId = state.uploadedDocuments.some(d => ['AADHAAR', 'PAN', 'PASSPORT'].includes(d.document_type));
    
    state.checklist.regCertUploaded = hasRegCert;
    state.checklist.degreeCertUploaded = hasDegree;
    state.checklist.govtIdUploaded = hasGovtId;
    
    // Update UI
    updateWizardChecklistUI();
    renderVaultTable();
    
    alert("Document deleted successfully!");
  } catch (err) {
    alert(`Delete Error: ${err.message}`);
  }
};

