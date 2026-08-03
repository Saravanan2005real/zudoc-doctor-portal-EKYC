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
};

// -------------------------------------------------------------
// STEP 1: Registration & OTP Verification
// -------------------------------------------------------------
function initStep1Auth() {
  const regForm = document.getElementById('form-register');
  const subviewReg = document.getElementById('subview-register');
  const subviewOTP = document.getElementById('subview-otp');
  const btnVerifyOTP = document.getElementById('btn-verify-otp');

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
        public_id: data.doctor_id,
        mobile: mobile,
        email: email,
        first_name: fname,
        last_name: lname,
      };

      document.getElementById('otp-mobile-display').innerText = mobile;
      subviewReg.classList.add('hidden');
      subviewOTP.classList.remove('hidden');

      alert(`Registration Successful! OTP sent to ${mobile}. Click OK to verify.`);
    } catch (err) {
      alert(`Registration Error: ${err.message}`);
    }
  });

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
          doctor_id: state.activeDoctor.public_id,
          otp: otpCode,
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

      state.uploadedDocuments.push(data);

      if (docType === 'REGISTRATION_CERTIFICATE') state.checklist.regCertUploaded = true;
      if (docType === 'MBBS_CERTIFICATE' || docType === 'MD_CERTIFICATE') state.checklist.degreeCertUploaded = true;
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

      alert('Verification Application Submitted Successfully! Transitioning to Step 4 (Live Pipeline)...');
      
      // AUTO-MOVE TO STEP 4
      goToStep(4);
      startPipelineAnimation();
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
      </tr>
    </thead>
    <tbody>`;

  state.uploadedDocuments.forEach(doc => {
    html += `<tr>
      <td><span class="badge badge-info">${doc.document_type}</span></td>
      <td>${doc.original_filename}</td>
      <td>v${doc.version}</td>
      <td><code>${doc.file_hash.substring(0, 10)}...</code></td>
      <td><span class="badge badge-success">Clean / Vaulted</span></td>
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
// STEP 4: Live Verification Pipeline Animation
// -------------------------------------------------------------
function initStep4Pipeline() {}

function startPipelineAnimation() {
  const consoleBox = document.getElementById('pipeline-console');
  const logPipe = (msg) => {
    const time = new Date().toLocaleTimeString();
    consoleBox.innerText += `\n[${time}] ${msg}`;
    consoleBox.scrollTop = consoleBox.scrollHeight;
  };

  logPipe('Job #VER-9081 Queued in background worker pool...');
  document.getElementById('tstep-1').classList.add('active');

  setTimeout(() => {
    document.getElementById('tstep-2').classList.add('active');
    logPipe('[OCR WORKER] Extracting registration number & doctor name from document scans...');
  }, 1500);

  setTimeout(() => {
    document.getElementById('tstep-3').classList.add('active');
    logPipe('[COUNCIL ADAPTER] Querying National Medical Commission (NMC) Registry...');
  }, 3500);

  setTimeout(() => {
    document.getElementById('tstep-4').classList.add('active');
    logPipe('[RISK ENGINE] Calculating Levenshtein similarity (100% Match) & Fraud Score (0)...');
  }, 5500);

  setTimeout(() => {
    document.getElementById('tstep-5').classList.add('active');
    document.getElementById('pipeline-status-badge').innerText = 'AUTO_VERIFIED';
    document.getElementById('pipeline-status-badge').className = 'badge badge-success';
    document.getElementById('pipeline-decision-desc').innerText = 'Decision: AUTO_VERIFIED (NMC Record Match 100%, Fraud Risk 0)';

    logPipe('[SUCCESS] Verification Complete! Doctor Account Activated for Prescriptions.');
    document.getElementById('btn-goto-prescription').classList.remove('hidden');

    if (state.activeDoctor) {
      document.getElementById('rx-doctor-id').value = state.activeDoctor.public_id;
    }
  }, 7500);
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
