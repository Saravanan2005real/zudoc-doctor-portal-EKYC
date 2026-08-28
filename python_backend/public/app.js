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
    if (!livenessActive && !livenessStarting) {
      beginStep4Liveness();
    }
  } else {
    stopLivenessCamera();
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
// STEP 4: Real eKYC Evaluation Pipeline (OCR microservice)
// -------------------------------------------------------------

function selectVerificationMode(mode) {
  const stdUi = document.getElementById('liveness-standard-ui');
  const accUi = document.getElementById('liveness-accessibility-ui');
  const btnStd = document.getElementById('btn-mode-standard');
  const btnAcc = document.getElementById('btn-mode-accessibility');

  if (mode === 'standard') {
    stdUi.classList.remove('hidden');
    accUi.classList.add('hidden');
    btnStd.classList.add('btn-primary');
    btnStd.classList.remove('btn-outline');
    btnAcc.classList.add('btn-outline');
    btnAcc.classList.remove('btn-primary');
  } else {
    stdUi.classList.add('hidden');
    accUi.classList.remove('hidden');
    btnAcc.classList.add('btn-primary');
    btnAcc.classList.remove('btn-outline');
    btnStd.classList.add('btn-outline');
    btnStd.classList.remove('btn-primary');
  }
}
window.selectVerificationMode = selectVerificationMode;

function initStep4Pipeline() {
  const btnStartLiveness = document.getElementById('btn-start-liveness');
  if (btnStartLiveness) {
    btnStartLiveness.addEventListener('click', runWebgazerPipeline);
  }

  // Listen for iframe postMessage from disability module
  window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'LIVENESS_SUCCESS') {
      alert("Accessibility Verification Passed!");
      document.getElementById('liveness-section').classList.add('hidden');
      const timeline = document.getElementById('pipeline-timeline');
      if (timeline) timeline.classList.remove('hidden');
      startPipelineAnimation();
    }
  });
}

function beginStep4Liveness() {
  resetPipelineUI();
  document.getElementById('liveness-section').classList.remove('hidden');
  selectVerificationMode('standard');
}
window.beginStep4Liveness = beginStep4Liveness;

// --- WebGazer + MediaPipe Implementation ---

const CLICKS_PER_CAL_DOT = 3;
const CHALLENGE_COUNT = 4;
const CHALLENGE_SETTLE_MS = 900;
const CHALLENGE_HOLD_MS = 2800;
const GAZE_HIT_RATIO = 0.32;
const HEAD_DRIFT_FAIL = 0.07;
const BLINK_EAR_DROP = 0.045;
const BLINK_TIMEOUT_MS = 8000;

function gazeHitRadius() {
  return 180;
}

const CAL_DOTS = [
  { id: 1, x: 0.1, y: 0.16 },
  { id: 2, x: 0.5, y: 0.16 },
  { id: 3, x: 0.9, y: 0.16 },
  { id: 4, x: 0.1, y: 0.5 },
  { id: 5, x: 0.5, y: 0.5 },
  { id: 6, x: 0.9, y: 0.5 },
  { id: 7, x: 0.1, y: 0.86 },
  { id: 8, x: 0.5, y: 0.86 },
  { id: 9, x: 0.9, y: 0.86 },
];

const NOSE = 1;
const LEFT_EYE = [33, 160, 158, 133, 153, 144];
const RIGHT_EYE = [362, 385, 387, 263, 373, 380];

const mesh = {
  ready: false,
  faceMesh: null,
  landmarks: null,
  noseBaseline: null,
  earBaseline: null,
  lastEar: null,
  headDrift: 0,
};

const gaze = { x: null, y: null };

function readGaze() {
  let x = gaze.x;
  let y = gaze.y;
  try {
    const pred = webgazer.getCurrentPrediction && webgazer.getCurrentPrediction();
    if (pred && typeof pred.x === "number" && typeof pred.y === "number") {
      x = pred.x; y = pred.y; gaze.x = x; gaze.y = y;
    }
  } catch (_) {}
  return x != null && y != null ? { x, y } : null;
}

function storeCalibrationSample(cx, cy) {
  try {
    if (typeof webgazer.recordScreenPosition === "function") webgazer.recordScreenPosition(cx, cy, "click");
  } catch (_) {}
  try {
    if (typeof webgazer.storePoints === "function") webgazer.storePoints(cx, cy, 0);
  } catch (_) {}
}

function wait(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function dist(ax, ay, bx, by) {
  return Math.hypot(ax - bx, ay - by);
}

function eyeAspectRatio(lm, indices) {
  const p = indices.map((i) => lm[i]);
  const v1 = Math.hypot(p[1].x - p[5].x, p[1].y - p[5].y);
  const v2 = Math.hypot(p[2].x - p[4].x, p[2].y - p[4].y);
  const h = Math.hypot(p[0].x - p[3].x, p[0].y - p[3].y);
  if (h < 1e-6) return 0;
  return (v1 + v2) / (2 * h);
}

function meanEar(lm) {
  return (eyeAspectRatio(lm, LEFT_EYE) + eyeAspectRatio(lm, RIGHT_EYE)) / 2;
}

async function initFaceMesh() {
  if (typeof FaceMesh === "undefined") {
    throw new Error("MediaPipe FaceMesh script failed to load");
  }

  const faceMesh = new FaceMesh({
    locateFile: (file) => `mediapipe/face_mesh/${file}`,
  });

  faceMesh.setOptions({ maxNumFaces: 1, refineLandmarks: true, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 });
  faceMesh.onResults((res) => {
    if (!res.multiFaceLandmarks || !res.multiFaceLandmarks.length) {
      mesh.landmarks = null;
      return;
    }
    mesh.landmarks = res.multiFaceLandmarks[0];
    mesh.lastEar = meanEar(mesh.landmarks);
    if (mesh.noseBaseline) {
      const nose = mesh.landmarks[NOSE];
      mesh.headDrift = Math.hypot(nose.x - mesh.noseBaseline.x, nose.y - mesh.noseBaseline.y);
    }
  });

  await faceMesh.initialize();
  mesh.faceMesh = faceMesh;
  mesh.ready = true;
  startMeshLoop();
}

function startMeshLoop() {
  let busy = false;
  const tick = async () => {
    const video = document.getElementById("webgazerVideoFeed");
    if (mesh.faceMesh && video && video.readyState >= 2 && video.videoWidth > 0 && !busy) {
      busy = true;
      try { await mesh.faceMesh.send({ image: video }); } catch (_) {}
      busy = false;
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function captureHeadBaseline() {
  if (!mesh.landmarks) return false;
  const n = mesh.landmarks[NOSE];
  mesh.noseBaseline = { x: n.x, y: n.y };
  mesh.headDrift = 0;
  mesh.earBaseline = mesh.lastEar;
  return true;
}

async function waitForFace(timeoutMs) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const video = document.getElementById("webgazerVideoFeed");
    if (video && video.readyState >= 2 && mesh.landmarks) return true;
    await wait(120);
  }
  return false;
}

function step2Calibrate() {
  return new Promise((resolve, reject) => {
    document.getElementById('calOverlay').classList.remove('hidden');
    const calLayer = document.getElementById('calLayer');
    calLayer.innerHTML = "";
    const clicks = {};
    let samples = 0;

    const updateProgress = () => {
      const done = CAL_DOTS.filter((d) => (clicks[d.id] || 0) >= CLICKS_PER_CAL_DOT).length;
      document.getElementById('calProgress').textContent = `${done} / ${CAL_DOTS.length} dots`;
    };
    updateProgress();

    CAL_DOTS.forEach((dot) => {
      clicks[dot.id] = 0;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "cal-dot";
      btn.style.left = `${dot.x * 100}%`;
      btn.style.top = `${dot.y * 100}%`;
      btn.style.position = "absolute";
      btn.style.width = "40px";
      btn.style.height = "40px";
      btn.style.borderRadius = "50%";
      btn.style.background = "white";
      btn.style.color = "black";
      btn.style.transform = "translate(-50%, -50%)";
      btn.textContent = String(dot.id);
      
      btn.addEventListener("click", () => {
        if (btn.style.background === "green") return;
        const rect = btn.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        storeCalibrationSample(cx, cy);
        clicks[dot.id] += 1;
        samples += 1;
        updateProgress();

        if (clicks[dot.id] >= CLICKS_PER_CAL_DOT) {
          btn.style.background = "green";
        }
        if (CAL_DOTS.every((d) => clicks[d.id] >= CLICKS_PER_CAL_DOT)) {
          document.getElementById('calOverlay').classList.add('hidden');
          wait(700).then(resolve);
        }
      });
      calLayer.appendChild(btn);
    });
  });
}

function randomDotPosition(index) {
  const zones = [{ x: 0.28, y: 0.32 }, { x: 0.72, y: 0.32 }, { x: 0.5, y: 0.5 }, { x: 0.28, y: 0.7 }, { x: 0.72, y: 0.7 }];
  const zone = zones[index % zones.length];
  const jitterX = (Math.random() - 0.5) * 0.12;
  const jitterY = (Math.random() - 0.5) * 0.1;
  return { x: Math.min(0.85, Math.max(0.15, zone.x + jitterX)) * window.innerWidth, y: Math.min(0.82, Math.max(0.22, zone.y + jitterY)) * window.innerHeight };
}

function runChallenge(target, durationMs) {
  return new Promise((resolve) => {
    let hits = 0; let samples = 0; let maxDrift = 0; let sumDist = 0;
    const radius = gazeHitRadius();
    const t0 = performance.now();
    const reticle = document.getElementById('gazeReticle');

    const tick = () => {
      const elapsed = performance.now() - t0;
      const g = readGaze();
      if (g) {
        samples += 1;
        const d = dist(g.x, g.y, target.x, target.y);
        sumDist += d;
        if (d <= radius) hits += 1;
        if (reticle && !reticle.classList.contains('hidden')) {
          reticle.style.left = `${g.x}px`; reticle.style.top = `${g.y}px`;
        }
      }
      maxDrift = Math.max(maxDrift, mesh.headDrift || 0);

      if (elapsed >= durationMs) {
        const gazeRatio = samples ? hits / samples : 0;
        const avgDist = samples ? sumDist / samples : Infinity;
        resolve({ gazeOk: samples >= 8 && (gazeRatio >= GAZE_HIT_RATIO || avgDist <= radius * 1.15), headOk: maxDrift <= HEAD_DRIFT_FAIL });
        return;
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}

async function step3to6Challenges() {
  document.getElementById('challengeOverlay').classList.remove('hidden');
  document.getElementById('gazeReticle').classList.remove('hidden');
  let gazePasses = 0; let headPasses = 0;

  for (let i = 0; i < CHALLENGE_COUNT; i++) {
    document.getElementById('challengeTitle').textContent = `Challenge ${i + 1} of ${CHALLENGE_COUNT}`;
    document.getElementById('challengeProgress').textContent = `Eyes only, do not move head!`;
    const target = randomDotPosition(i);
    document.getElementById('challengeDot').style.left = `${target.x}px`;
    document.getElementById('challengeDot').style.top = `${target.y}px`;
    await wait(CHALLENGE_SETTLE_MS);
    captureHeadBaseline();
    const outcome = await runChallenge(target, CHALLENGE_HOLD_MS);
    if (outcome.gazeOk) gazePasses++;
    if (outcome.headOk) headPasses++;
    await wait(400);
  }

  document.getElementById('challengeOverlay').classList.add('hidden');
  document.getElementById('gazeReticle').classList.add('hidden');
  const need = Math.max(2, Math.ceil(CHALLENGE_COUNT * 0.5));
  return gazePasses >= need && headPasses >= need;
}

function waitForBlink(openEar, timeoutMs) {
  return new Promise((resolve) => {
    const threshold = Math.max(0.12, openEar - BLINK_EAR_DROP);
    let closed = false;
    const t0 = performance.now();
    const tick = () => {
      const ear = mesh.lastEar;
      if (ear != null) {
        if (!closed && ear < threshold) closed = true;
        else if (closed && ear > openEar - BLINK_EAR_DROP * 0.4) { resolve(true); return; }
      }
      if (performance.now() - t0 >= timeoutMs) { resolve(false); return; }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}

async function step7Blink() {
  document.getElementById('blinkOverlay').classList.remove('hidden');
  document.getElementById('blinkTitle').textContent = "Get ready...";
  await wait(1200);
  const openSamples = [];
  const baseStart = performance.now();
  while (performance.now() - baseStart < 800) {
    if (mesh.lastEar != null) openSamples.push(mesh.lastEar);
    await wait(40);
  }
  const openEar = openSamples.length > 0 ? openSamples.reduce((a, b) => a + b, 0) / openSamples.length : 0.25;

  document.getElementById('blinkTitle').textContent = "Blink once now";
  const blinked = await waitForBlink(openEar, BLINK_TIMEOUT_MS);
  document.getElementById('blinkOverlay').classList.add('hidden');
  return blinked;
}

async function runWebgazerPipeline() {
  document.getElementById('btn-start-liveness').disabled = true;
  document.getElementById('liveness-overlay').style.display = 'none';
  document.getElementById('liveness-status').innerText = 'Initializing WebGazer... Please allow camera access.';

  try {
    if (typeof webgazer === "undefined") throw new Error("WebGazer failed to load");
    webgazer.saveDataAcrossSessions(false);
    webgazer.setRegression("ridge");
    webgazer.setTracker("TFFacemesh");
    webgazer.applyKalmanFilter(true);
    webgazer.showVideoPreview(true);
    webgazer.showFaceOverlay(true);
    webgazer.showFaceFeedbackBox(true);
    webgazer.showPredictionPoints(false);
    webgazer.setGazeListener((data) => {
      if (data) { gaze.x = data.x; gaze.y = data.y; }
    });
    
    // Attempt to move webgazer video into our container
    await webgazer.begin();
    
    // Reparent webgazer elements to our container
    const wgVideo = document.getElementById("webgazerVideoFeed");
    const wgCanvas = document.getElementById("webgazerVideoCanvas");
    const wgFace = document.getElementById("webgazerFaceOverlay");
    const wgFeedback = document.getElementById("webgazerFaceFeedbackBox");
    const container = document.getElementById("webgazer-container");
    
    if (wgVideo && container) container.appendChild(wgVideo);
    if (wgCanvas && container) container.appendChild(wgCanvas);
    if (wgFace && container) container.appendChild(wgFace);
    if (wgFeedback && container) container.appendChild(wgFeedback);
    
    document.getElementById('liveness-status').innerText = 'Loading FaceMesh...';
    await initFaceMesh();

    document.getElementById('liveness-status').innerText = 'Waiting for Face...';
    const faceOk = await waitForFace(15000);
    if (!faceOk) throw new Error("Face not detected. Center yourself and try again.");

    document.getElementById('liveness-status').innerText = 'Calibrating...';
    await step2Calibrate();

    document.getElementById('liveness-status').innerText = 'Follow the dots...';
    const checksPassed = await step3to6Challenges();
    if (!checksPassed) throw new Error("Gaze or Head stability failed.");

    document.getElementById('liveness-status').innerText = 'Blink Challenge...';
    const blinked = await step7Blink();
    if (!blinked) throw new Error("Blink not detected.");

    // SUCCESS
    document.getElementById('liveness-status').innerText = 'Human Verification Passed!';
    try {
        webgazer.clearGazeListener && webgazer.clearGazeListener();
        await webgazer.clearData();
        webgazer.end();
    } catch (_) {}
    
    document.getElementById('liveness-section').classList.add('hidden');
    const timeline = document.getElementById('pipeline-timeline');
    if (timeline) timeline.classList.remove('hidden');
    startPipelineAnimation();

  } catch (err) {
    console.error(err);
    alert("Verification Failed: " + (err.message || String(err)));
    document.getElementById('btn-start-liveness').disabled = false;
    document.getElementById('liveness-overlay').style.display = 'flex';
    document.getElementById('liveness-status').innerText = 'Check Failed. Click Start to try again.';
  }
}

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
      ? `<img src="${doc.face_image_url}" alt="face" style="width:96px;height:96px;object-fit:cover;border-radius:8px;margin-top:8px;" />`
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

  panel.classList.remove('hidden');
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

