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
  step41Complete: false,
  liveIdResult: null,
  liveFaceCheck: null,
  liveFrame: null,
  gazeSummary: null,
  livenessResult: null,
  livenessMode: null,
};

let pipelineRunning = false;

const API_BASE = window.location.origin;

// DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initStep1Auth();
  initStep2Credentials();
  initStep3Vault();
  initStep4Pipeline();
  initStep5Prescription();

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
    if (!state.step41Complete) {
      beginStep4Liveness();
    }
  } else {
    stopIdHoldCamera();
    if (typeof stopLivenessCamera === 'function') {
      stopLivenessCamera();
    }
  }

  if (stepNum === 3) {
    refreshVaultFromServer();
  }
};

// Documents vaulted in earlier sessions must be visible here, otherwise a stale
// ID sits in the database where the doctor can neither see nor delete it, and
// then surfaces unexpectedly in the Step 4 results.
async function refreshVaultFromServer() {
  if (!state.activeDoctor || !state.activeDoctor.public_id) return;
  try {
    const resp = await fetch(`${API_BASE}/api/v1/doctors/documents`, {
      headers: { 'X-Doctor-Public-ID': state.activeDoctor.public_id },
    });
    if (!resp.ok) return;
    const docs = await resp.json();
    if (!Array.isArray(docs)) return;

    const sessionIds = new Set(state.uploadedDocuments.map((d) => d.document_id));
    docs.forEach((doc) => {
      if (!sessionIds.has(doc.document_id)) {
        state.uploadedDocuments.push({ ...doc, fromPreviousSession: true });
      }
    });

    state.checklist.regCertUploaded = state.uploadedDocuments.some((d) => d.document_type === 'REGISTRATION_CERTIFICATE');
    state.checklist.degreeCertUploaded = state.uploadedDocuments.some((d) => d.document_type === 'MEDICAL_DEGREE_CERTIFICATE');
    state.checklist.govtIdUploaded = state.uploadedDocuments.some((d) => ['AADHAAR', 'PAN', 'PASSPORT'].includes(d.document_type));

    updateWizardChecklistUI();
    renderVaultTable();
  } catch (_) {
    // Vault hydration is best-effort; uploads still work without it.
  }
}

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
      <td>${doc.fromPreviousSession
        ? '<span class="badge badge-warning">Earlier session</span>'
        : '<span class="badge badge-success">Clean / Vaulted</span>'}</td>
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
  if (mode === 'standard') {
    if (stdUi) stdUi.classList.remove('hidden');
    if (accUi) accUi.classList.add('hidden');
  } else {
    if (stdUi) stdUi.classList.add('hidden');
    if (accUi) accUi.classList.remove('hidden');
  }
}
window.selectVerificationMode = selectVerificationMode;

function initStep4Pipeline() {
  const btnStartLiveness = document.getElementById('btn-start-liveness');
  if (btnStartLiveness) {
    btnStartLiveness.addEventListener('click', runWebgazerPipeline);
  }

  const btnCapture = document.getElementById('btn-capture-live-id');
  if (btnCapture) {
    btnCapture.addEventListener('click', captureAndVerifyLiveId);
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

let livenessActive = false;
let livenessStarting = false;

function stopLivenessCamera() {
  livenessActive = false;
  livenessStarting = false;

  try {
    if (typeof webgazer !== 'undefined') {
      if (typeof webgazer.clearGazeListener === 'function') webgazer.clearGazeListener();
      if (typeof webgazer.end === 'function') webgazer.end();
    }
  } catch (_) {}

  ['webgazerVideoFeed', 'ekyc-cam-feed'].forEach((id) => {
    const video = document.getElementById(id);
    if (video && video.srcObject) {
      try {
        video.srcObject.getTracks().forEach((t) => t.stop());
      } catch (_) {}
      video.srcObject = null;
    }
  });
  mesh.landmarks = null;
  if (typeof resetGaze === 'function') resetGaze();
  if (typeof stopSpeech === 'function') stopSpeech();

  const overlays = ['challengeOverlay', 'gazeReticle', 'blinkOverlay', 'calOverlay', 'wg-boot-overlay', 'audioOverlay'];
  overlays.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
  });
  document.documentElement.style.overflow = '';
  document.body.style.overflow = '';
}
window.stopLivenessCamera = stopLivenessCamera;

function stopIdHoldCamera() {
  const video = document.getElementById('live-id-webcam');
  if (video && video.srcObject) {
    try {
      video.srcObject.getTracks().forEach((t) => t.stop());
    } catch (_) {}
    video.srcObject = null;
  }
}

async function startIdHoldCamera() {
  const video = document.getElementById('live-id-webcam');
  if (!video) return;
  if (video.srcObject) return;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
    });
    video.srcObject = stream;
  } catch (err) {
    alert('Webcam access denied or unavailable: ' + (err.message || err));
  }
}

function beginStep4Liveness() {
  state.step41Complete = false;
  state.gazeSummary = null;
  state.livenessResult = null;
  state.liveIdResult = null;
  state.liveFaceCheck = null;
  state.liveFrame = null;
  state.livenessMode = null;
  resetPipelineUI();
  const liveId = document.getElementById('live-id-section');
  const liveness = document.getElementById('liveness-section');
  const timeline = document.getElementById('pipeline-timeline');
  const choice = document.getElementById('liveness-mode-choice');
  if (liveId) liveId.classList.remove('hidden');
  if (liveness) liveness.classList.add('hidden');
  if (choice) choice.classList.add('hidden');
  if (timeline) timeline.classList.add('hidden');
  const tick = document.getElementById('live-id-tick');
  if (tick) tick.classList.add('hidden');
  const btn = document.getElementById('btn-capture-live-id');
  if (btn) {
    btn.disabled = false;
    btn.classList.remove('hidden');
  }
  startIdHoldCamera();
}
window.beginStep4Liveness = beginStep4Liveness;

function proceedToStep42() {
  stopIdHoldCamera();
  const liveId = document.getElementById('live-id-section');
  if (liveId) liveId.classList.add('hidden');
  const choice = document.getElementById('liveness-mode-choice');
  if (!choice) {
    runWebgazerPipeline();
    return;
  }
  choice.classList.remove('hidden');
  const first = document.getElementById('btn-mode-eye');
  if (first) first.focus();

  // The picker has to be usable without seeing it, otherwise the accessible
  // path is unreachable for the people it exists for.
  speak('Choose a verification method. Press 1 for the eye tracking check, or press 2 for the audio guided check.');
  document.addEventListener('keydown', modeChoiceKeyHandler);
}

function modeChoiceKeyHandler(event) {
  const choice = document.getElementById('liveness-mode-choice');
  if (!choice || choice.classList.contains('hidden')) {
    document.removeEventListener('keydown', modeChoiceKeyHandler);
    return;
  }
  if (event.key === '1') chooseLivenessMode('eye');
  if (event.key === '2') chooseLivenessMode('audio');
}

window.chooseLivenessMode = function (mode) {
  document.removeEventListener('keydown', modeChoiceKeyHandler);
  stopSpeech();
  const choice = document.getElementById('liveness-mode-choice');
  if (choice) choice.classList.add('hidden');
  const liveness = document.getElementById('liveness-section');
  if (liveness) liveness.classList.remove('hidden');
  state.livenessMode = mode === 'audio' ? 'audio' : 'eye';

  const standard = document.getElementById('liveness-standard-ui');
  const accessible = document.getElementById('liveness-accessibility-ui');
  if (state.livenessMode === 'audio') {
    if (standard) standard.classList.add('hidden');
    if (accessible) accessible.classList.remove('hidden');
    runAudioLivenessPipeline();
  } else {
    if (accessible) accessible.classList.add('hidden');
    if (standard) standard.classList.remove('hidden');
    runWebgazerPipeline();
  }
};

function grabFrameDataUrl(video) {
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 1280;
  canvas.height = video.videoHeight || 720;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg', 0.9);
}

// Runs while the user is already in Step 4.2, so the eye-tracking flow never
// waits on RetinaFace. The verdict is picked up when the results panel renders.
function startLiveFaceCheck(dataUrl) {
  state.liveFaceCheck = fetch(`${API_BASE}/api/v1/live_face_check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: dataUrl }),
  })
    .then(async (resp) => {
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok || data.person_detected === undefined) {
        const detail = data.error || data.detail || `HTTP ${resp.status}`;
        throw new Error(
          resp.status === 404 || resp.status === 405
            ? 'live face check endpoint not found — restart the portal (python main.py)'
            : detail
        );
      }
      return data;
    })
    .then((data) => {
      state.liveIdResult = data;
      return data;
    })
    .catch((err) => {
      state.liveIdResult = { status: 'failed', error: err.message };
      return state.liveIdResult;
    });
}

async function captureAndVerifyLiveId() {
  const video = document.getElementById('live-id-webcam');
  const btn = document.getElementById('btn-capture-live-id');
  const tick = document.getElementById('live-id-tick');
  if (!video || video.readyState < 2) {
    alert('Camera is not ready yet. Allow camera access and try again.');
    return;
  }

  if (btn) btn.disabled = true;
  if (tick) tick.classList.remove('hidden');

  let dataUrl = null;
  try {
    dataUrl = grabFrameDataUrl(video);
  } catch (err) {
    console.warn('Frame capture failed:', err);
  }

  state.step41Complete = true;
  state.liveFrame = dataUrl;
  if (dataUrl) {
    state.liveIdResult = { status: 'pending' };
    startLiveFaceCheck(dataUrl);
  } else {
    state.liveIdResult = { status: 'failed', error: 'Could not read a frame from the camera' };
  }

  await wait(900);
  proceedToStep42();
}

// --- WebGazer + MediaPipe Implementation ---

const CAL_HOVER_MS = 2000;
const CAL_SAMPLE_INTERVAL_MS = 80;
const CAL_MIN_VALID_PER_DOT = 10;
const GAZE_SMOOTH = 0.28;
const GAZE_SPIKE_PX = 420;
const CHALLENGE_COUNT = 4;
const CHALLENGE_SETTLE_MS = 900;
const CHALLENGE_HOLD_MS = 2800;
const GAZE_HIT_RATIO = 0.22;
const HEAD_DRIFT_FAIL = 0.12;
const BLINK_EAR_DROP = 0.045;
const BLINK_TIMEOUT_MS = 8000;

function gazeHitRadius() {
  return 180;
}

const CAL_DOTS = [
  { id: 1, x: 0, y: 0 },
  { id: 2, x: 0.5, y: 0 },
  { id: 3, x: 1, y: 0 },
  { id: 4, x: 0, y: 0.5 },
  { id: 5, x: 0.5, y: 0.5 },
  { id: 6, x: 1, y: 0.5 },
  { id: 7, x: 0, y: 1 },
  { id: 8, x: 0.5, y: 1 },
  { id: 9, x: 1, y: 1 },
];

const NOSE = 1;
const LEFT_EYE = [33, 160, 158, 133, 153, 144];
const RIGHT_EYE = [362, 385, 387, 263, 373, 380];

const mesh = {
  ready: false,
  loopRunning: false,
  faceMesh: null,
  landmarks: null,
  noseBaseline: null,
  earBaseline: null,
  lastEar: null,
  headDrift: 0,
};

const gaze = { x: null, y: null, at: 0 };
const gazeSmooth = { x: null, y: null };
const wgPred = { x: null, y: null, at: 0 };

// --- Iris-based gaze model -------------------------------------------------
// WebGazer's own ridge regression is very noisy on laptop webcams, so the 9-dot
// calibration also trains a small ridge model on MediaPipe iris landmarks and
// that model drives the reticle whenever it is available.

const IRIS_L = [468, 469, 470, 471, 472];
const IRIS_R = [473, 474, 475, 476, 477];
const GAZE_FEATURES = 7;
const GAZE_RIDGE_LAMBDA = 1e-4;
const GAZE_MIN_SAMPLES = 45;
const GAZE_STALE_MS = 700;

const gazeModel = { ready: false, wx: null, wy: null, samples: [], source: 'none' };

function centroid(lm, idx) {
  let x = 0;
  let y = 0;
  for (const i of idx) {
    if (!lm[i]) return null;
    x += lm[i].x;
    y += lm[i].y;
  }
  return { x: x / idx.length, y: y / idx.length };
}

function meshFeatures(lm) {
  if (!lm || !lm[477]) return null;
  const li = centroid(lm, IRIS_L);
  const ri = centroid(lm, IRIS_R);
  if (!li || !ri) return null;

  const lOuter = lm[33];
  const lInner = lm[133];
  const lUp = lm[159];
  const lLow = lm[145];
  const rInner = lm[362];
  const rOuter = lm[263];
  const rUp = lm[386];
  const rLow = lm[374];
  if (!lOuter || !lInner || !lUp || !lLow || !rInner || !rOuter || !rUp || !rLow) return null;

  const safe = (v) => (Math.abs(v) < 1e-6 ? 1e-6 : v);
  const exL = (li.x - lOuter.x) / safe(lInner.x - lOuter.x);
  const eyL = (li.y - lUp.y) / safe(lLow.y - lUp.y);
  const exR = (ri.x - rInner.x) / safe(rOuter.x - rInner.x);
  const eyR = (ri.y - rUp.y) / safe(rLow.y - rUp.y);

  const nose = lm[NOSE];
  if (!nose) return null;
  const midX = (lOuter.x + rOuter.x) / 2;
  const midY = (lOuter.y + rOuter.y) / 2;
  const iod = safe(Math.hypot(rOuter.x - lOuter.x, rOuter.y - lOuter.y));
  const yaw = (nose.x - midX) / iod;
  const pitch = (nose.y - midY) / iod;

  const f = [1, exL, eyL, exR, eyR, yaw, pitch];
  return f.every((v) => Number.isFinite(v)) ? f : null;
}

function solveLinearSystem(A, b) {
  const n = b.length;
  const M = A.map((row, i) => row.concat([b[i]]));
  for (let c = 0; c < n; c++) {
    let pivot = c;
    for (let r = c + 1; r < n; r++) {
      if (Math.abs(M[r][c]) > Math.abs(M[pivot][c])) pivot = r;
    }
    if (Math.abs(M[pivot][c]) < 1e-12) return null;
    const tmp = M[c];
    M[c] = M[pivot];
    M[pivot] = tmp;
    for (let r = 0; r < n; r++) {
      if (r === c) continue;
      const factor = M[r][c] / M[c][c];
      if (!factor) continue;
      for (let k = c; k <= n; k++) M[r][k] -= factor * M[c][k];
    }
  }
  const out = new Array(n);
  for (let i = 0; i < n; i++) out[i] = M[i][n] / M[i][i];
  return out.every((v) => Number.isFinite(v)) ? out : null;
}

function fitRidge(rows, targets) {
  const n = GAZE_FEATURES;
  const A = Array.from({ length: n }, () => new Array(n).fill(0));
  const b = new Array(n).fill(0);
  for (let k = 0; k < rows.length; k++) {
    const f = rows[k];
    for (let i = 0; i < n; i++) {
      b[i] += f[i] * targets[k];
      for (let j = 0; j < n; j++) A[i][j] += f[i] * f[j];
    }
  }
  const scale = Math.max(1, rows.length);
  for (let i = 1; i < n; i++) A[i][i] += GAZE_RIDGE_LAMBDA * scale;
  return solveLinearSystem(A, b);
}

function trainGazeModel() {
  const rows = gazeModel.samples.map((s) => s.f);
  if (rows.length < GAZE_MIN_SAMPLES) return false;
  const wx = fitRidge(rows, gazeModel.samples.map((s) => s.x));
  const wy = fitRidge(rows, gazeModel.samples.map((s) => s.y));
  if (!wx || !wy) return false;
  // Reject a model that cannot even reproduce its own training points: that
  // means the user moved their head around during calibration and its
  // predictions would be worse than WebGazer's.
  let sq = 0;
  for (const s of gazeModel.samples) {
    sq += (applyWeights(wx, s.f) - s.x) ** 2 + (applyWeights(wy, s.f) - s.y) ** 2;
  }
  const rms = Math.sqrt(sq / gazeModel.samples.length);
  const diag = Math.hypot(window.innerWidth, window.innerHeight);
  if (!Number.isFinite(rms) || rms > diag * 0.35) return false;

  gazeModel.wx = wx;
  gazeModel.wy = wy;
  gazeModel.ready = true;
  gazeModel.rms = rms;
  return true;
}

function applyWeights(w, f) {
  let sum = 0;
  for (let i = 0; i < GAZE_FEATURES; i++) sum += w[i] * f[i];
  return sum;
}

function meshGazePoint() {
  if (!gazeModel.ready || !mesh.landmarks) return null;
  const f = meshFeatures(mesh.landmarks);
  if (!f) return null;
  const x = applyWeights(gazeModel.wx, f);
  const y = applyWeights(gazeModel.wy, f);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  const margin = 260;
  return {
    x: Math.min(window.innerWidth + margin, Math.max(-margin, x)),
    y: Math.min(window.innerHeight + margin, Math.max(-margin, y)),
  };
}

function ingestGaze(data) {
  if (!data || !Number.isFinite(data.x) || !Number.isFinite(data.y)) return;
  if (gazeSmooth.x == null) {
    gazeSmooth.x = data.x;
    gazeSmooth.y = data.y;
  } else {
    const jump = Math.hypot(data.x - gazeSmooth.x, data.y - gazeSmooth.y);
    const alpha = jump > GAZE_SPIKE_PX ? 0.12 : GAZE_SMOOTH;
    gazeSmooth.x = alpha * data.x + (1 - alpha) * gazeSmooth.x;
    gazeSmooth.y = alpha * data.y + (1 - alpha) * gazeSmooth.y;
  }
  gaze.x = gazeSmooth.x;
  gaze.y = gazeSmooth.y;
  gaze.at = performance.now();
}

function resetGaze() {
  gaze.x = null;
  gaze.y = null;
  gaze.at = 0;
  gazeSmooth.x = null;
  gazeSmooth.y = null;
  wgPred.x = null;
  wgPred.y = null;
  wgPred.at = 0;
}

function rawGaze() {
  const meshPoint = meshGazePoint();
  if (meshPoint) {
    gazeModel.source = 'iris';
    return meshPoint;
  }
  let pred = null;
  try {
    pred = typeof webgazer !== 'undefined' && webgazer.getCurrentPrediction ? webgazer.getCurrentPrediction() : null;
  } catch (_) {}
  if (!pred && wgPred.x != null && performance.now() - wgPred.at < GAZE_STALE_MS) pred = wgPred;
  if (pred && Number.isFinite(pred.x) && Number.isFinite(pred.y)) {
    gazeModel.source = 'webgazer';
    return { x: pred.x, y: pred.y };
  }
  return null;
}

function readGaze() {
  const raw = rawGaze();
  if (raw) ingestGaze(raw);
  if (gaze.x == null || performance.now() - gaze.at > GAZE_STALE_MS) return null;
  return { x: gaze.x, y: gaze.y };
}

function storeCalibrationSample(cx, cy) {
  if (mesh.landmarks) {
    const f = meshFeatures(mesh.landmarks);
    if (f) gazeModel.samples.push({ f, x: cx, y: cy });
  }
  try {
    if (typeof webgazer !== 'undefined' && typeof webgazer.recordScreenPosition === 'function') {
      webgazer.recordScreenPosition(cx, cy, 'click');
    }
  } catch (_) {}
}

function calDotPoint(dot) {
  const padX = Math.max(40, Math.round(window.innerWidth * 0.07));
  const padY = Math.max(72, Math.round(window.innerHeight * 0.12));
  const x = padX + dot.x * (window.innerWidth - 2 * padX);
  const y = padY + dot.y * (window.innerHeight - 2 * padY);
  return { x, y };
}

// WebGazer's own DOM stays exactly where WebGazer put it: reparenting the
// <video> pauses playback in Chrome and starves both trackers. Hiding is done
// purely in CSS (off-screen, opacity 0, display kept as block).
function hideWebgazerUi() {
  const video = document.getElementById('webgazerVideoFeed');
  if (!video) return;
  video.muted = true;
  video.playsInline = true;
  if (video.paused) {
    const play = video.play();
    if (play && typeof play.catch === 'function') play.catch(() => {});
  }
}

const overlayHomes = new WeakMap();

function attachFullscreenOverlay(el) {
  if (!el) return;
  if (!overlayHomes.has(el) && el.parentElement && el.parentElement !== document.body) {
    overlayHomes.set(el, el.parentElement);
  }
  document.body.appendChild(el);
  el.classList.remove('hidden');
  document.documentElement.style.overflow = 'hidden';
  document.body.style.overflow = 'hidden';
  hideWebgazerUi();
}

function detachFullscreenOverlay(el) {
  if (!el) return;
  el.classList.add('hidden');
  const home = overlayHomes.get(el) || document.getElementById('liveness-standard-ui');
  if (home && el.parentElement !== home) home.appendChild(el);
  document.documentElement.style.overflow = '';
  document.body.style.overflow = '';
}

function hideCalOverlay() {
  detachFullscreenOverlay(document.getElementById('calOverlay'));
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
  if (mesh.ready && mesh.faceMesh) {
    startMeshLoop();
    return;
  }
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
    if (!mesh.loggedShape) {
      mesh.loggedShape = true;
      console.info(
        `FaceMesh landmarks: ${mesh.landmarks.length}${mesh.landmarks.length >= 478 ? ' (iris available)' : ' (no iris — gaze falls back to WebGazer)'}`
      );
    }
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

function getTrackingVideo() {
  const wg = document.getElementById('webgazerVideoFeed');
  if (wg && wg.readyState >= 2 && wg.videoWidth > 0) return wg;
  const own = document.getElementById('ekyc-cam-feed');
  if (own && own.readyState >= 2 && own.videoWidth > 0) return own;
  return null;
}

// Fallback camera: if WebGazer never manages to open the webcam, tracking still
// needs frames for the iris model and blink detection.
async function ensureFallbackCamera() {
  const wg = document.getElementById('webgazerVideoFeed');
  if (wg && wg.readyState >= 2 && wg.videoWidth > 0) return true;
  let video = document.getElementById('ekyc-cam-feed');
  if (video && video.srcObject) return true;
  if (!video) {
    video = document.createElement('video');
    video.id = 'ekyc-cam-feed';
    video.autoplay = true;
    video.muted = true;
    video.playsInline = true;
    document.body.appendChild(video);
  }
  try {
    video.srcObject = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
    });
    await video.play().catch(() => {});
    return true;
  } catch (_) {
    return false;
  }
}

function startMeshLoop() {
  if (mesh.loopRunning) return;
  mesh.loopRunning = true;
  let busy = false;
  const tick = async () => {
    const video = getTrackingVideo();
    if (mesh.faceMesh && video && !busy) {
      busy = true;
      try {
        await mesh.faceMesh.send({ image: video });
      } catch (_) {}
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

async function waitForFace(timeoutMs, onProgress) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    if (getTrackingVideo() && mesh.landmarks && meshFeatures(mesh.landmarks)) return true;
    if (onProgress) {
      const left = Math.max(0, Math.ceil((timeoutMs - (Date.now() - t0)) / 1000));
      onProgress(getTrackingVideo() ? `Looking for your face… ${left}s` : `Waiting for camera… ${left}s`);
    }
    await wait(150);
  }
  return false;
}

function step2Calibrate() {
  return new Promise((resolve, reject) => {
    const overlay = document.getElementById('calOverlay');
    const calLayer = document.getElementById('calLayer');
    if (!overlay || !calLayer) {
      reject(new Error('Calibration overlay missing'));
      return;
    }

    attachFullscreenOverlay(overlay);
    calLayer.innerHTML = '';
    gazeModel.samples = [];
    gazeModel.ready = false;

    const completed = {};
    let finished = false;
    const hoverState = { id: null, raf: 0, samples: 0, valid: 0 };

    const faceState = document.getElementById('calFaceState');
    const faceWatch = setInterval(() => {
      if (!faceState) return;
      const ok = !!mesh.landmarks;
      faceState.textContent = ok ? 'Face detected' : 'Face not detected — move into the light';
      faceState.className = ok ? 'cal-face-ok' : 'cal-face-bad';
    }, 250);

    const updateProgress = () => {
      const done = CAL_DOTS.filter((d) => completed[d.id]).length;
      const el = document.getElementById('calProgress');
      if (el) el.textContent = `${done} / ${CAL_DOTS.length} dots`;
    };
    updateProgress();

    const stopHover = (btn) => {
      hoverState.id = null;
      if (hoverState.raf) cancelAnimationFrame(hoverState.raf);
      hoverState.raf = 0;
      hoverState.samples = 0;
      hoverState.valid = 0;
      if (btn && !btn.classList.contains('cal-done')) btn.style.setProperty('--cal-pct', '0%');
    };

    const finishAll = () => {
      if (finished) return;
      finished = true;
      clearInterval(faceWatch);
      window.removeEventListener('resize', layoutDots);
      const trained = trainGazeModel();
      console.info(
        trained
          ? `Gaze model trained on ${gazeModel.samples.length} iris samples (rms ${Math.round(gazeModel.rms)}px)`
          : `Gaze model not trained (${gazeModel.samples.length} samples) — falling back to WebGazer`
      );
      hideCalOverlay();
      wait(400).then(resolve);
    };

    const layoutDots = () => {
      CAL_DOTS.forEach((dot) => {
        const btn = calLayer.querySelector(`[data-cal-id="${dot.id}"]`);
        if (!btn) return;
        const pt = calDotPoint(dot);
        btn.style.left = `${pt.x}px`;
        btn.style.top = `${pt.y}px`;
      });
    };

    CAL_DOTS.forEach((dot) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'cal-dot';
      btn.dataset.calId = String(dot.id);
      btn.textContent = String(dot.id);
      btn.style.setProperty('--cal-pct', '0%');
      const pt = calDotPoint(dot);
      btn.style.left = `${pt.x}px`;
      btn.style.top = `${pt.y}px`;

      const tick = (startedAt) => {
        if (hoverState.id !== dot.id || finished || completed[dot.id]) return;
        const elapsed = performance.now() - startedAt;
        const pct = Math.min(100, (elapsed / CAL_HOVER_MS) * 100);
        btn.style.setProperty('--cal-pct', `${pct}%`);

        const rect = btn.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const before = gazeModel.samples.length;
        if (elapsed - hoverState.samples * CAL_SAMPLE_INTERVAL_MS >= CAL_SAMPLE_INTERVAL_MS) {
          storeCalibrationSample(cx, cy);
          hoverState.samples += 1;
          if (gazeModel.samples.length > before) hoverState.valid += 1;
        }

        // Give the dot more time when the face is not being tracked, so a dot is
        // never "completed" without any usable training data behind it.
        const enough = hoverState.valid >= CAL_MIN_VALID_PER_DOT;
        if (elapsed >= CAL_HOVER_MS && (enough || elapsed >= CAL_HOVER_MS * 2.5)) {
          completed[dot.id] = true;
          btn.classList.add('cal-done');
          btn.style.setProperty('--cal-pct', '100%');
          storeCalibrationSample(cx, cy);
          stopHover(btn);
          updateProgress();
          if (CAL_DOTS.every((d) => completed[d.id])) finishAll();
          return;
        }
        hoverState.raf = requestAnimationFrame(() => tick(startedAt));
      };

      btn.addEventListener('pointerenter', () => {
        if (completed[dot.id] || finished) return;
        hoverState.id = dot.id;
        hoverState.samples = 0;
        hoverState.valid = 0;
        const rect = btn.getBoundingClientRect();
        storeCalibrationSample(rect.left + rect.width / 2, rect.top + rect.height / 2);
        hoverState.raf = requestAnimationFrame(() => tick(performance.now()));
      });
      btn.addEventListener('pointerleave', () => {
        if (completed[dot.id]) return;
        stopHover(btn);
      });
      btn.addEventListener('click', (e) => e.preventDefault());

      calLayer.appendChild(btn);
    });

    window.addEventListener('resize', layoutDots);
  });
}

function randomDotPosition(index) {
  const zones = [{ x: 0.28, y: 0.32 }, { x: 0.72, y: 0.32 }, { x: 0.5, y: 0.5 }, { x: 0.28, y: 0.7 }, { x: 0.72, y: 0.7 }];
  const zone = zones[index % zones.length];
  const jitterX = (Math.random() - 0.5) * 0.12;
  const jitterY = (Math.random() - 0.5) * 0.1;
  return { x: Math.min(0.85, Math.max(0.15, zone.x + jitterX)) * window.innerWidth, y: Math.min(0.82, Math.max(0.22, zone.y + jitterY)) * window.innerHeight };
}

function trackReticle(active) {
  const reticle = document.getElementById('gazeReticle');
  if (!reticle) return () => {};
  reticle.classList.remove('hidden');
  let raf = 0;
  const tick = () => {
    const g = readGaze();
    if (g) {
      reticle.classList.remove('searching');
      reticle.style.left = `${g.x}px`;
      reticle.style.top = `${g.y}px`;
      const t = active();
      const locked = t && dist(g.x, g.y, t.x, t.y) <= gazeHitRadius();
      reticle.classList.toggle('locked', !!locked);
    } else {
      reticle.classList.add('searching');
      reticle.classList.remove('locked');
    }
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  return () => {
    cancelAnimationFrame(raf);
    reticle.classList.add('hidden');
    reticle.classList.remove('locked', 'searching');
  };
}

function runChallenge(target, durationMs) {
  return new Promise((resolve) => {
    let hits = 0;
    let samples = 0;
    let maxDrift = 0;
    let sumDist = 0;
    const radius = gazeHitRadius();
    const t0 = performance.now();
    const progress = document.getElementById('challengeProgress');

    const tick = () => {
      const elapsed = performance.now() - t0;
      const g = readGaze();
      if (g) {
        samples += 1;
        const d = dist(g.x, g.y, target.x, target.y);
        sumDist += d;
        if (d <= radius) hits += 1;
      }
      maxDrift = Math.max(maxDrift, mesh.headDrift || 0);

      if (progress) {
        const pct = Math.round(Math.min(100, (elapsed / durationMs) * 100));
        progress.textContent = samples
          ? `Tracking ${pct}%  ·  on target ${Math.round((hits / samples) * 100)}%`
          : 'Looking for your eyes…';
      }

      if (elapsed >= durationMs) {
        const gazeRatio = samples ? hits / samples : 0;
        const avgDist = samples ? sumDist / samples : Infinity;
        resolve({
          gazeOk: samples >= 8 && (gazeRatio >= GAZE_HIT_RATIO || avgDist <= radius * 1.15),
          headOk: maxDrift <= HEAD_DRIFT_FAIL,
          samples,
        });
        return;
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}

async function step3to6Challenges() {
  const overlay = document.getElementById('challengeOverlay');
  const dotEl = document.getElementById('challengeDot');
  attachFullscreenOverlay(overlay);

  let target = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
  const stopReticle = trackReticle(() => target);
  let gazePasses = 0;
  let headPasses = 0;

  try {
    for (let i = 0; i < CHALLENGE_COUNT; i++) {
      hideWebgazerUi();
      document.getElementById('challengeTitle').textContent = `Look here  ·  ${i + 1} / ${CHALLENGE_COUNT}`;
      document.getElementById('challengeHint').textContent = 'Watch the orange dot. Keep your head still.';
      document.getElementById('challengeProgress').textContent = 'Get ready…';
      target = randomDotPosition(i);
      if (dotEl) {
        dotEl.style.left = `${target.x}px`;
        dotEl.style.top = `${target.y}px`;
      }
      await wait(CHALLENGE_SETTLE_MS);
      captureHeadBaseline();
      const outcome = await runChallenge(target, CHALLENGE_HOLD_MS);
      if (outcome.gazeOk) gazePasses++;
      if (outcome.headOk) headPasses++;
      await wait(400);
    }
  } finally {
    stopReticle();
    detachFullscreenOverlay(overlay);
  }

  state.gazeSummary = { gazePasses, headPasses, total: CHALLENGE_COUNT, source: gazeModel.source };
  return true;
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
  const overlay = document.getElementById('blinkOverlay');
  const title = document.getElementById('blinkTitle');
  const hint = document.getElementById('blinkHint');
  attachFullscreenOverlay(overlay);
  hideWebgazerUi();
  title.textContent = 'Get ready...';
  hint.textContent = 'Face the screen. Blink once when asked.';
  await wait(1200);
  const openSamples = [];
  const baseStart = performance.now();
  while (performance.now() - baseStart < 800) {
    if (mesh.lastEar != null) openSamples.push(mesh.lastEar);
    await wait(40);
  }
  const openEar = openSamples.length > 0 ? openSamples.reduce((a, b) => a + b, 0) / openSamples.length : 0.25;

  title.textContent = 'Blink once now';
  let blinked = await waitForBlink(openEar, BLINK_TIMEOUT_MS / 2);
  if (!blinked) {
    hint.textContent = 'Blink not detected yet — try one more clear blink.';
    blinked = await waitForBlink(openEar, BLINK_TIMEOUT_MS / 2);
  }

  title.textContent = blinked ? 'Blink detected' : 'Blink not detected';
  hint.textContent = blinked ? 'Liveness signal captured.' : 'Continuing — this will be flagged in the report.';
  await wait(700);
  detachFullscreenOverlay(overlay);
  return blinked;
}

// --- Accessible (audio guided) liveness -----------------------------------
// Same goal as the eye-tracking check, but nothing has to be seen on screen:
// spoken prompts ask for head turns and blinks, which are measured from the
// MediaPipe face mesh.

const AUDIO_YAW_THRESHOLD = 0.10;
const AUDIO_TURN_TIMEOUT_MS = 14000;
const AUDIO_BLINK_TARGET = 2;
const AUDIO_BLINK_TIMEOUT_MS = 14000;

function speak(text) {
  try {
    if (!('speechSynthesis' in window)) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
  } catch (_) {}
}

function stopSpeech() {
  try {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  } catch (_) {}
}

let audioCtx = null;

// Short tones so a blind user gets feedback without waiting for speech.
function playTone(frequency, durationMs) {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    audioCtx = audioCtx || new Ctx();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.frequency.value = frequency;
    osc.type = 'sine';
    gain.gain.value = 0.08;
    osc.connect(gain).connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + durationMs / 1000);
  } catch (_) {}
}

const chime = {
  ok: () => playTone(880, 180),
  fail: () => playTone(220, 300),
  next: () => playTone(560, 120),
};

// Robust yaw estimation directly from face mesh geometry:
// Does NOT require iris landmarks (works with standard 468 landmarks)
// Combines nose-eye projection with lateral cheek distance asymmetry
function currentYaw() {
  if (!mesh.landmarks || mesh.landmarks.length < 468) return null;
  const lm = mesh.landmarks;
  const nose = lm[1];     // Tip of nose
  const lOuter = lm[33];   // Outer eye corner (viewer left)
  const rOuter = lm[263];  // Outer eye corner (viewer right)
  if (!nose || !lOuter || !rOuter) return null;

  // Eye-nose horizontal offset normalized by eye span
  const midEyeX = (lOuter.x + rOuter.x) / 2;
  const iod = Math.max(1e-4, Math.hypot(rOuter.x - lOuter.x, rOuter.y - lOuter.y));
  const eyeYaw = (nose.x - midEyeX) / iod;

  // Cheek asymmetry: distance from nose tip to each cheek boundary
  const lCheek = lm[234];
  const rCheek = lm[454];
  if (lCheek && rCheek) {
    const dLeft = Math.hypot(nose.x - lCheek.x, nose.y - lCheek.y);
    const dRight = Math.hypot(nose.x - rCheek.x, nose.y - rCheek.y);
    const cheekYaw = (dRight - dLeft) / Math.max(1e-4, dRight + dLeft);
    const combined = 0.5 * eyeYaw + 0.5 * cheekYaw;
    return Number.isFinite(combined) ? combined : eyeYaw;
  }
  return Number.isFinite(eyeYaw) ? eyeYaw : null;
}

// Calibrates baseline resting yaw over time to prevent single-frame spikes
async function measureBaselineYaw(durationMs = 700) {
  const samples = [];
  const t0 = performance.now();
  while (performance.now() - t0 < durationMs) {
    const y = currentYaw();
    if (y != null && Number.isFinite(y)) samples.push(y);
    await wait(30);
  }
  return samples.length > 0
    ? samples.reduce((a, b) => a + b, 0) / samples.length
    : (currentYaw() ?? 0);
}

function announce(instruction, status) {
  const instrEl = document.getElementById('audioInstruction');
  const statusEl = document.getElementById('audioStatus');
  if (instrEl && instruction != null) instrEl.textContent = instruction;
  if (statusEl && status != null) statusEl.textContent = status;
}

function renderAudioSteps(total, doneCount, activeIndex) {
  const box = document.getElementById('audioStepDots');
  if (!box) return;
  let html = '';
  for (let i = 0; i < total; i++) {
    const cls = i < doneCount ? 'done' : i === activeIndex ? 'active' : '';
    html += `<span class="${cls}"></span>`;
  }
  box.innerHTML = html;
}

// Waits for a head turn away from the baseline and back to centre. Accepts
// either direction (webcam feeds are mirrored inconsistently), optionally
// requiring the opposite side to the previous turn.
function waitForHeadTurn(baseline, forbidSign, timeoutMs) {
  return new Promise((resolve) => {
    const t0 = performance.now();
    let peak = 0;
    let peakSign = 0;
    let turned = false;

    const tick = () => {
      const yaw = currentYaw();
      if (yaw != null) {
        const delta = yaw - baseline;
        const sign = Math.sign(delta);

        if (!turned) {
          // Check if head turned sufficiently from baseline in permitted direction
          if (Math.abs(delta) >= AUDIO_YAW_THRESHOLD && (forbidSign === 0 || sign !== forbidSign)) {
            turned = true;
            peak = Math.abs(delta);
            peakSign = sign;
            chime.next();
            announce('Good turn detected! Now return to the centre.', 'Turn detected — Face forward');
            speak('Good. Now face forward again.');
          }
        } else {
          // Track peak amplitude while turned
          if (Math.abs(delta) > peak) peak = Math.abs(delta);

          // Return to centre is satisfied when delta returns close to baseline
          if (Math.abs(delta) <= AUDIO_YAW_THRESHOLD * 0.50) {
            resolve({ ok: true, sign: peakSign, peak });
            return;
          }
        }
      }

      if (performance.now() - t0 >= timeoutMs) {
        // If a strong turn was detected and user returned substantially, resolve as success
        if (turned && peak >= AUDIO_YAW_THRESHOLD * 1.1) {
          resolve({ ok: true, sign: peakSign, peak });
          return;
        }
        resolve({ ok: false, sign: peakSign, peak });
        return;
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}

function waitForBlinks(openEar, count, timeoutMs) {
  return new Promise((resolve) => {
    const threshold = Math.max(0.12, openEar - BLINK_EAR_DROP);
    const t0 = performance.now();
    let closed = false;
    let blinks = 0;

    const tick = () => {
      const ear = mesh.lastEar;
      if (ear != null) {
        if (!closed && ear < threshold) {
          closed = true;
        } else if (closed && ear > openEar - BLINK_EAR_DROP * 0.4) {
          closed = false;
          blinks += 1;
          chime.next();
          announce(null, `${blinks} of ${count} blinks detected`);
          if (blinks >= count) {
            resolve(blinks);
            return;
          }
        }
      }
      if (performance.now() - t0 >= timeoutMs) {
        resolve(blinks);
        return;
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}

async function measureOpenEar(durationMs) {
  const samples = [];
  const t0 = performance.now();
  while (performance.now() - t0 < durationMs) {
    if (mesh.lastEar != null) samples.push(mesh.lastEar);
    await wait(40);
  }
  return samples.length ? samples.reduce((a, b) => a + b, 0) / samples.length : 0.25;
}

async function runAudioLivenessPipeline() {
  livenessStarting = true;
  const overlay = document.getElementById('audioOverlay');
  attachFullscreenOverlay(overlay);
  renderAudioSteps(3, 0, -1);

  const checks = [
    { label: 'Face detected and tracked live', passed: false },
    { label: 'First head turn completed', passed: false },
    { label: 'Second head turn to the other side', passed: false },
    { label: 'Two deliberate blinks detected', passed: false },
  ];

  try {
    announce('Getting the camera ready.', 'Starting…');
    speak('Audio verification. Please face the camera and listen for instructions.');

    await ensureFallbackCamera();
    try {
      await initFaceMesh();
    } catch (err) {
      console.warn('FaceMesh unavailable:', err);
    }
    if (!getTrackingVideo()) await ensureFallbackCamera();

    livenessStarting = false;
    livenessActive = true;

    const faceFound = await waitForFace(20000, (msg) => announce(null, msg));
    checks[0].passed = !!faceFound;
    if (!faceFound) {
      announce('Face not detected.', 'Could not find your face');
      speak('I could not find your face. Please make sure the camera is not covered.');
      chime.fail();
      await wait(2500);
    } else {
      chime.ok();
      announce('Hold still facing the camera.', 'Calibrating center position…');
      speak('Thank you, I can see you. Hold still facing forward.');
      await wait(1200);
    }

    // Measure stable baseline yaw across multiple frames
    const baseline1 = await measureBaselineYaw(800);

    // Turn one: accept left or right
    renderAudioSteps(3, 0, 0);
    announce('Slowly turn your head to your left or right, then back to the centre.', 'Waiting for a head turn');
    speak('Slowly turn your head to your left or right, then bring it back to the centre.');
    const turn1 = await waitForHeadTurn(baseline1, 0, AUDIO_TURN_TIMEOUT_MS);
    checks[1].passed = turn1.ok;
    if (turn1.ok) {
      chime.ok();
      renderAudioSteps(3, 1, 1);
      speak('Great.');
    } else {
      chime.fail();
      renderAudioSteps(3, 0, 1);
      speak('I did not detect that turn. Let us continue.');
    }
    await wait(1000);

    // Re-center baseline before Turn 2
    announce('Face forward for the next check.', 'Centering…');
    const baseline2 = await measureBaselineYaw(500);

    // Turn two: require opposite direction to whatever was detected in turn 1
    const promptSide = turn1.ok ? 'the other side' : 'your right';
    announce(`Now turn your head to ${promptSide}, then back to the centre.`, 'Waiting for opposite turn');
    speak(`Now turn your head to ${promptSide}, then back to the centre.`);
    const turn2 = await waitForHeadTurn(baseline2, turn1.ok ? turn1.sign : 0, AUDIO_TURN_TIMEOUT_MS);
    checks[2].passed = turn2.ok;
    if (turn2.ok) {
      chime.ok();
      renderAudioSteps(3, 2, 2);
      speak('Perfect.');
    } else {
      chime.fail();
      speak('I did not detect that turn. Moving on.');
    }
    await wait(1000);

    // Blinks
    announce('Please blink twice, slowly.', 'Waiting for two blinks');
    speak('Last step. Please blink twice, slowly.');
    const openEar = await measureOpenEar(700);
    const blinks = await waitForBlinks(openEar, AUDIO_BLINK_TARGET, AUDIO_BLINK_TIMEOUT_MS);
    checks[3].passed = blinks >= AUDIO_BLINK_TARGET;
    checks[3].detail = `${blinks}/${AUDIO_BLINK_TARGET} blinks`;
    renderAudioSteps(3, checks[3].passed ? 3 : 2, -1);

    const passed = checks.filter((c) => c.passed).length;
    let verdict = 'NOT_CONFIRMED';
    if (checks[0].passed && checks[3].passed && (checks[1].passed || checks[2].passed)) verdict = 'REAL_PERSON';
    else if (checks[0].passed && (checks[3].passed || checks[1].passed || checks[2].passed)) verdict = 'LIKELY_REAL';

    state.livenessResult = {
      verdict,
      checks,
      confidence: Math.round((passed / checks.length) * 100),
      tracker: 'audio-guided (face mesh)',
      calibrated: true,
      mode: 'audio',
    };

    if (verdict === 'NOT_CONFIRMED') {
      chime.fail();
      announce('Verification could not be confirmed.', 'Not confirmed');
      speak('I could not confirm the checks. The result will be sent for manual review.');
    } else {
      chime.ok();
      announce('Verification complete. Thank you.', 'Complete');
      speak('Verification complete. Thank you.');
    }
    await wait(2200);
  } catch (err) {
    console.error(err);
  } finally {
    stopSpeech();
    detachFullscreenOverlay(overlay);
    const accessible = document.getElementById('liveness-accessibility-ui');
    if (accessible) accessible.classList.add('hidden');
    if (!state.livenessResult) {
      state.livenessResult = {
        verdict: 'NOT_CONFIRMED',
        checks,
        confidence: 0,
        tracker: 'audio-guided (face mesh)',
        calibrated: false,
        mode: 'audio',
      };
    }
    await finishLivenessAndPipeline();
  }
}

// Turns the raw Step 4.2 measurements into the "is this a real person" verdict
// shown in the Step 4 report.
function buildLivenessVerdict(faceFound, blinked) {
  const summary = state.gazeSummary || { gazePasses: 0, headPasses: 0, total: CHALLENGE_COUNT, source: 'none' };
  const gazeFollowed = summary.gazePasses > 0;
  const headStill = summary.headPasses >= Math.ceil(summary.total / 2);

  const checks = [
    { label: 'Face detected and tracked live', passed: !!faceFound },
    { label: 'Eyes followed the moving target', passed: gazeFollowed, detail: `${summary.gazePasses}/${summary.total} targets` },
    { label: 'Head stayed still (no photo swap)', passed: headStill, detail: `${summary.headPasses}/${summary.total} checks` },
    { label: 'Spontaneous blink detected', passed: !!blinked },
  ];

  const passed = checks.filter((c) => c.passed).length;
  let verdict = 'NOT_CONFIRMED';
  if (faceFound && blinked && gazeFollowed) verdict = 'REAL_PERSON';
  else if (faceFound && (blinked || gazeFollowed)) verdict = 'LIKELY_REAL';

  return {
    verdict,
    checks,
    confidence: Math.round((passed / checks.length) * 100),
    tracker: summary.source,
    calibrated: !!gazeModel.ready,
  };
}

async function finishLivenessAndPipeline() {
  detachFullscreenOverlay(document.getElementById('wg-boot-overlay'));
  detachFullscreenOverlay(document.getElementById('challengeOverlay'));
  detachFullscreenOverlay(document.getElementById('blinkOverlay'));
  hideCalOverlay();
  stopLivenessCamera();
  const liveSec = document.getElementById('liveness-section');
  if (liveSec) liveSec.classList.add('hidden');
  const timeline = document.getElementById('pipeline-timeline');
  if (timeline) timeline.classList.remove('hidden');
  await startPipelineAnimation();
}

async function startWebgazer() {
  if (typeof webgazer === 'undefined') return false;
  try {
    if (typeof webgazer.end === 'function') webgazer.end();
  } catch (_) {}

  try {
    webgazer.saveDataAcrossSessions(false);
    webgazer.setRegression('ridge');
    webgazer.setTracker('TFFacemesh');
    webgazer.applyKalmanFilter(true);
    if (webgazer.params) {
      webgazer.params.showVideo = false;
      webgazer.params.showFaceOverlay = false;
      webgazer.params.showFaceFeedbackBox = false;
      webgazer.params.showGazeDot = false;
    }
    webgazer.setGazeListener((data) => {
      if (!data || !Number.isFinite(data.x) || !Number.isFinite(data.y)) return;
      wgPred.x = data.x;
      wgPred.y = data.y;
      wgPred.at = performance.now();
    });

    let timedOut = false;
    await Promise.race([
      webgazer.begin(),
      wait(12000).then(() => {
        timedOut = true;
      }),
    ]);

    // These only work once begin() has built the DOM, so they run after.
    try {
      webgazer.showVideoPreview(false);
      webgazer.showFaceOverlay(false);
      webgazer.showFaceFeedbackBox(false);
      webgazer.showPredictionPoints(false);
    } catch (_) {}
    hideWebgazerUi();
    return !timedOut;
  } catch (err) {
    console.warn('WebGazer failed to start:', err);
    return false;
  }
}

async function runWebgazerPipeline() {
  livenessStarting = true;
  const boot = document.getElementById('wg-boot-overlay');
  const status = document.getElementById('wgBootStatus');
  const setStatus = (text) => {
    if (status) status.textContent = text;
  };
  attachFullscreenOverlay(boot);
  resetGaze();
  gazeModel.ready = false;
  gazeModel.samples = [];

  try {
    setStatus('Starting camera…');
    const wgOk = await startWebgazer();
    livenessStarting = false;
    livenessActive = true;
    if (!wgOk) {
      setStatus('Opening camera directly…');
      await ensureFallbackCamera();
    }

    setStatus('Loading face landmarks…');
    try {
      await initFaceMesh();
    } catch (err) {
      console.warn('FaceMesh unavailable:', err);
    }

    if (!getTrackingVideo()) await ensureFallbackCamera();

    const faceFound = await waitForFace(15000, setStatus);
    if (!faceFound) {
      setStatus('Face not detected — continuing anyway');
      await wait(900);
    } else {
      setStatus('Ready');
      await wait(300);
    }

    hideWebgazerUi();
    detachFullscreenOverlay(boot);
    await step2Calibrate();
    await step3to6Challenges();
    const blinked = await step7Blink();
    state.livenessResult = buildLivenessVerdict(faceFound, blinked);
  } catch (err) {
    console.error(err);
  } finally {
    if (!state.livenessResult) state.livenessResult = buildLivenessVerdict(!!mesh.landmarks, false);
    detachFullscreenOverlay(boot);
    await finishLivenessAndPipeline();
  }
}

function resetPipelineUI() {
  for (let i = 1; i <= 5; i++) {
    const el = document.getElementById(`tstep-${i}`);
    if (el) el.classList.remove('active', 'failed', 'warn');
  }
  const badge = document.getElementById('pipeline-status-badge');
  if (badge) {
    badge.innerText = 'RUNNING';
    badge.className = 'badge badge-warning';
  }
  const desc = document.getElementById('pipeline-decision-desc');
  if (desc) desc.innerText = 'Waiting for eKYC model evaluation...';
  const consoleBox = document.getElementById('pipeline-console');
  if (consoleBox) consoleBox.innerText = '[SYSTEM] Starting eKYC evaluation pipeline...';
  const btnRx = document.getElementById('btn-goto-prescription');
  if (btnRx) btnRx.classList.add('hidden');
  const panel = document.getElementById('ekyc-result-panel');
  if (panel) panel.classList.add('hidden');
  const cards = document.getElementById('ekyc-result-cards');
  if (cards) cards.innerHTML = '';
  const livePanel = document.getElementById('live-person-panel');
  if (livePanel) livePanel.classList.add('hidden');
  const liveCard = document.getElementById('live-person-card');
  if (liveCard) liveCard.innerHTML = '';
}

function logPipe(msg) {
  const consoleBox = document.getElementById('pipeline-console');
  if (!consoleBox) return;
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

const LIVE_VERDICT_LABELS = {
  REAL_PERSON: { text: 'REAL PERSON CONFIRMED', badge: 'badge-success' },
  LIKELY_REAL: { text: 'LIKELY REAL — PARTIAL SIGNALS', badge: 'badge-warning' },
  NOT_CONFIRMED: { text: 'NOT CONFIRMED', badge: 'badge-danger' },
};

function renderLivePersonCard() {
  const panel = document.getElementById('live-person-panel');
  const card = document.getElementById('live-person-card');
  if (!panel || !card) return;

  const liveness = state.livenessResult;
  const faceCheck = state.liveIdResult || {};
  let verdictKey = liveness ? liveness.verdict : 'NOT_CONFIRMED';
  // A frame with no live face in it overrides the eye-tracking result: the
  // Step 4.1 check can land after the verdict was first computed.
  if (faceCheck.person_detected === false) verdictKey = 'NOT_CONFIRMED';
  const verdict = LIVE_VERDICT_LABELS[verdictKey] || LIVE_VERDICT_LABELS.NOT_CONFIRMED;

  const mark = (ok) => (ok
    ? '<span style="color:#22c55e;font-weight:700;">PASS</span>'
    : '<span style="color:#ef4444;font-weight:700;">FAIL</span>');

  const checks = (liveness ? liveness.checks : []).map((c) => `
      <li style="margin:0.2rem 0;">
        ${mark(c.passed)} &nbsp;${c.label}${c.detail ? ` <span class="text-muted">(${c.detail})</span>` : ''}
      </li>`).join('');

  const thumb = (src, caption) => `
    <figure style="margin:0;text-align:center;">
      <img src="${src}" alt="${caption}" style="width:96px;height:96px;object-fit:cover;border-radius:8px;" />
      <figcaption class="text-muted" style="font-size:0.75rem;">${caption}</figcaption>
    </figure>`;

  // Step 4.1 is presented as evidence, not prose: the captured frame, plus the
  // detected crops and their pass/fail rows only when detection actually ran.
  let detection = '';
  const crops = [];

  if (state.liveFrame) {
    crops.push(`<img src="${state.liveFrame}" alt="captured frame" style="width:220px;max-width:100%;border-radius:8px;" />`);
  }

  if (faceCheck.person_detected !== undefined) {
    const conf = faceCheck.person_confidence != null ? ` (${Math.round(faceCheck.person_confidence * 100)}% confidence)` : '';
    detection = `
      <ul style="list-style:none;padding:0;margin:0.25rem 0;">
        <li style="margin:0.2rem 0;">${mark(!!faceCheck.person_detected)} &nbsp;Live face present in the captured frame${conf}</li>
        <li style="margin:0.2rem 0;">${mark(!!faceCheck.id_card_photo_detected)} &nbsp;Photo detected on the held ID card</li>
      </ul>`;
    if (faceCheck.person_face_image_url) crops.push(thumb(faceCheck.person_face_image_url, 'Live face'));
    if (faceCheck.id_card_face_image_url) crops.push(thumb(faceCheck.id_card_face_image_url, 'Photo on card'));
  }

  const step41 = `
    ${detection}
    ${crops.length ? `<div style="display:flex;gap:0.75rem;margin-top:0.5rem;flex-wrap:wrap;align-items:flex-end;">${crops.join('')}</div>` : ''}`;

  card.innerHTML = `
    <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">
      <span class="badge ${verdict.badge}" style="font-size:0.85rem;">${verdict.text}</span>
      ${liveness ? `<span class="text-muted">${liveness.confidence}% of liveness signals passed</span>` : ''}
    </div>
    <h4 style="margin:0.75rem 0 0.25rem;font-size:0.95rem;">Step 4.1 — Person holding the ID card</h4>
    ${step41}
    <h4 style="margin:0.75rem 0 0.25rem;font-size:0.95rem;">Step 4.2 — Active liveness (${
      (liveness && liveness.mode === 'audio') || state.livenessMode === 'audio'
        ? 'audio guided: head turns + blinks'
        : 'eye tracking + blink'
    })</h4>
    ${checks
      ? `<ul style="list-style:none;padding:0;margin:0.25rem 0;">${checks}</ul>`
      : '<p class="text-muted" style="margin:0.25rem 0;">Liveness checks did not run.</p>'}
    ${liveness ? `<p class="text-muted" style="margin:0.5rem 0 0;font-size:0.8rem;">Tracker: ${liveness.tracker}${liveness.calibrated ? ' (calibrated)' : ' (uncalibrated)'}</p>` : ''}
  `;

  panel.classList.remove('hidden');
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
    const procHtml = doc.processed_image_url
      ? `<img src="${doc.processed_image_url}" alt="document" style="width:100%;max-height:160px;object-fit:contain;border-radius:8px;margin-top:8px;" />`
      : '';
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
        ${procHtml}
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

  const timeline = document.getElementById('pipeline-timeline');
  if (timeline) timeline.classList.remove('hidden');
  resetPipelineUI();
  if (timeline) timeline.classList.remove('hidden');

  activateStage(1, 'done', 'Verification package submitted');
  logPipe(`[STEP 1] Application loaded for doctor ${state.activeDoctor.public_id}`);
  logPipe(state.liveFrame
    ? '[STEP 4.1] Live ID hold captured (camera frame stored).'
    : '[STEP 4.1] Live ID hold step completed, but no camera frame was captured.');
  if (state.livenessMode) {
    logPipe(`[STEP 4.2] Mode chosen: ${state.livenessMode === 'audio' ? 'audio guided (accessible)' : 'eye tracking'}.`);
  }
  if (state.gazeSummary) {
    const g = state.gazeSummary;
    logPipe(
      `[STEP 4.2] Eye tracking: ${g.gazePasses}/${g.total} gaze targets, ${g.headPasses}/${g.total} head-still checks (tracker: ${g.source}).`
    );
  }

  // Show the liveness verdict straight away, then refresh it once the Step 4.1
  // frame analysis (started while the user was doing the eye tracking) lands.
  renderLivePersonCard();
  if (state.livenessResult) {
    logPipe(`[LIVENESS] Verdict: ${state.livenessResult.verdict} (${state.livenessResult.confidence}% of signals passed).`);
    state.livenessResult.checks.forEach((c) => {
      logPipe(`[LIVENESS] ${c.passed ? 'PASS' : 'FAIL'} ${c.label}${c.detail ? ` — ${c.detail}` : ''}`);
    });
  }
  if (state.liveFaceCheck) {
    Promise.race([state.liveFaceCheck, wait(25000)]).then(() => {
      const r = state.liveIdResult || {};
      if (r.person_detected !== undefined) {
        logPipe(
          `[STEP 4.1] Live face ${r.person_detected ? 'detected' : 'NOT detected'}; ID card photo ${r.id_card_photo_detected ? 'detected' : 'not detected'} (detector: ${r.detector || 'n/a'}).`
        );
      } else if (r.error) {
        console.warn('Step 4.1 face detection unavailable:', r.error);
      }
      renderLivePersonCard();
    });
  }

  logPipe('[STEP 2] Running eKYC evaluation on uploaded documents...');
  activateStage(2, 'running', 'Running OCR model on uploaded KYC documents...');

  // Only evaluate what was uploaded in this session, otherwise documents left
  // in the vault from earlier sessions show up in the results.
  const sessionDocs = state.uploadedDocuments.filter((d) => d && d.document_id && !d.fromPreviousSession);
  const sessionDocIds = sessionDocs.map((d) => d.document_id);
  if (sessionDocIds.length) {
    const types = [...new Set(sessionDocs.map((d) => d.document_type))].join(', ');
    logPipe(`[SCOPE] Evaluating ${sessionDocIds.length} document(s) uploaded in this session: ${types}`);
  } else {
    logPipe('[SCOPE] No documents uploaded in this session — evaluating the existing vault contents.');
  }

  try {
    const resp = await fetch(`${API_BASE}/api/v1/doctors/evaluate-ekyc`, {
      method: 'POST',
      headers: {
        'X-Doctor-Public-ID': state.activeDoctor.public_id,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ document_ids: sessionDocIds }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const detail = data.error || data.detail || data.message || `HTTP ${resp.status}`;
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }

    logPipe('[CONNECTED] eKYC evaluation responded OK');
    (data.stages || []).forEach((stage) => {
      activateStage(stage.id, stage.status, stage.detail);
      logPipe(`[STAGE ${stage.id}] ${stage.title}: ${stage.detail}`);
    });

    const docs = Array.isArray(data.documents) ? data.documents.slice() : [];
    if (state.liveIdResult && state.liveIdResult.parsed_fields) {
      docs.unshift({
        document_type: 'LIVE_ID_HOLD',
        status: state.liveIdResult.status || 'success',
        parsed_fields: state.liveIdResult.parsed_fields,
        ocr_confidence: '-',
        face_image_url: state.liveIdResult.holder_face_image_url || state.liveIdResult.face_image_url,
        processed_image_url: state.liveIdResult.processed_image_url,
        raw_text: state.liveIdResult.raw_text || [],
      });
    }
    renderEkycResults(docs);

    const decision = (data.decision && data.decision.result) || data.status || 'UNKNOWN';
    const badge = document.getElementById('pipeline-status-badge');
    if (badge) {
      badge.innerText = decision;
      if (decision === 'AUTO_VERIFIED') {
        badge.className = 'badge badge-success';
      } else if (decision === 'MANUAL_REVIEW') {
        badge.className = 'badge badge-warning';
      } else {
        badge.className = 'badge badge-danger';
      }
    }

    const conf = data.decision ? data.decision.ocr_confidence : '-';
    const nameScore = data.decision ? data.decision.name_match_score : '-';
    const desc = document.getElementById('pipeline-decision-desc');
    if (desc) {
      desc.innerText = `Decision: ${decision} (OCR ${conf}%, Name Match ${nameScore}%)`;
    }

    logPipe(`[DECISION] ${data.message || decision}`);

    if (decision === 'AUTO_VERIFIED' || decision === 'MANUAL_REVIEW') {
      const btnRx = document.getElementById('btn-goto-prescription');
      if (btnRx) btnRx.classList.remove('hidden');
      if (state.activeDoctor) {
        const rx = document.getElementById('rx-doctor-id');
        if (rx) rx.value = state.activeDoctor.public_id;
      }
      logPipe('[SUCCESS] Step 5 unlocked. You can continue to Digital Prescription Studio.');
    } else {
      logPipe('[BLOCKED] Evaluation failed. Re-upload clearer KYC documents and retry from Step 3.');
    }
  } catch (err) {
    activateStage(2, 'failed', err.message);
    activateStage(5, 'failed', `Evaluation error: ${err.message}`);
    const badge = document.getElementById('pipeline-status-badge');
    if (badge) {
      badge.innerText = 'FAILED';
      badge.className = 'badge badge-danger';
    }
    logPipe(`[ERROR] ${err.message}`);
    if (state.liveIdResult) {
      logPipe('[INFO] Showing Step 4.1 live capture results even though uploaded-doc OCR failed.');
    }
  } finally {
    pipelineRunning = false;
    if (timeline) timeline.classList.remove('hidden');
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

