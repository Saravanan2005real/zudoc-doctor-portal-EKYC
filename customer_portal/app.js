const availableModules = [
    { id: 'ocr', name: 'Document OCR', desc: 'Extract data from Aadhaar, PAN, and passports.' },
    { id: 'liveness', name: 'Liveness Detection', desc: 'Verify user presence via eye-tracking or video.' },
    { id: 'cross_match', name: 'Cross-Matching', desc: 'Match face and extracted data for high confidence.' },
    { id: 'fraud_analysis', name: 'Fraud Analysis', desc: 'Deep scan for tampering, deepfakes, and synthetic media.' }
];

let pipeline = [];

const moduleListEl = document.getElementById('available-modules');
const canvasEl = document.getElementById('pipeline-canvas');
const emptyCanvasEl = document.getElementById('canvas-empty');
const generateBtn = document.getElementById('generate-btn');
const clearBtn = document.getElementById('clear-btn');

// Config Modal Elements
const configModal = document.getElementById('config-modal');
const configFormContainer = document.getElementById('config-form-container');
const configModalTitle = document.getElementById('config-modal-title');
const cancelConfigBtn = document.getElementById('cancel-config-btn');
const saveConfigBtn = document.getElementById('save-config-btn');
let currentConfigModuleId = null;

const modal = document.getElementById('link-modal');
const closeModalBtn = document.getElementById('close-modal');
const copyBtn = document.getElementById('copy-btn');
const previewBtn = document.getElementById('preview-btn');
const generatedLinkEl = document.getElementById('generated-link');

// Render Available Modules
function renderAvailableModules() {
    moduleListEl.innerHTML = '';
    availableModules.forEach(mod => {
        const div = document.createElement('div');
        div.className = 'module-item';
        div.innerHTML = `
            <div class="module-info">
                <h4>${mod.name}</h4>
                <p>${mod.desc}</p>
            </div>
            <div class="module-add">+</div>
        `;
        div.onclick = () => addModuleToPipeline(mod);
        moduleListEl.appendChild(div);
    });
}

// Add to Pipeline
function addModuleToPipeline(mod) {
    let defaultConfig = {};
    if (mod.id === 'ocr') {
        defaultConfig = { aadhaar: true, pan: true, passport: false, company: false, gst: false };
    } else if (mod.id === 'liveness') {
        defaultConfig = { mode: 'eye_tracking' };
    } else if (mod.id === 'cross_match') {
        defaultConfig = { match_face: true, match_name: true };
    } else if (mod.id === 'fraud_analysis') {
        defaultConfig = { deep_scan: true, synthetic_check: true };
    }
    
    pipeline.push({ ...mod, uniqueId: Date.now() + Math.random(), config: defaultConfig });
    renderPipeline();
}

// Remove from Pipeline
function removeModule(event, uniqueId) {
    if (event) event.stopPropagation();
    pipeline = pipeline.filter(m => m.uniqueId !== uniqueId);
    renderPipeline();
}

// Clear Pipeline
clearBtn.addEventListener('click', () => {
    pipeline = [];
    renderPipeline();
});

// Render Pipeline Canvas
function renderPipeline() {
    // Clear everything except empty state
    Array.from(canvasEl.children).forEach(child => {
        if (child.id !== 'canvas-empty') {
            canvasEl.removeChild(child);
        }
    });

    if (pipeline.length === 0) {
        emptyCanvasEl.style.display = 'block';
        generateBtn.disabled = true;
    } else {
        emptyCanvasEl.style.display = 'none';
        generateBtn.disabled = false;

        pipeline.forEach((mod, index) => {
            const node = document.createElement('div');
            node.className = 'pipeline-node';
            node.onclick = () => openConfigModal(mod.uniqueId);
            node.innerHTML = `
                <h4>${index + 1}. ${mod.name}</h4>
                <button class="remove-node" onclick="removeModule(event, ${mod.uniqueId})">&times;</button>
            `;
            canvasEl.appendChild(node);

            // Add connector line if not the last item
            if (index < pipeline.length - 1) {
                const connector = document.createElement('div');
                connector.className = 'pipeline-connector';
                canvasEl.appendChild(connector);
            }
        });
    }
}

// Config Modal Logic
function openConfigModal(uniqueId) {
    const mod = pipeline.find(m => m.uniqueId === uniqueId);
    if (!mod) return;
    
    currentConfigModuleId = uniqueId;
    configModalTitle.textContent = `Configure ${mod.name}`;
    
    let html = '<div class="config-group">';
    const c = mod.config || {};
    
    if (mod.id === 'ocr') {
        html += `
            <label class="config-label"><input type="checkbox" id="cfg-aadhaar" ${c.aadhaar ? 'checked' : ''}> Aadhaar (UIDAI)</label>
            <label class="config-label"><input type="checkbox" id="cfg-pan" ${c.pan ? 'checked' : ''}> PAN Card</label>
            <label class="config-label"><input type="checkbox" id="cfg-passport" ${c.passport ? 'checked' : ''}> Passport</label>
            <label class="config-label"><input type="checkbox" id="cfg-company" ${c.company ? 'checked' : ''}> Company Certificate</label>
            <label class="config-label"><input type="checkbox" id="cfg-gst" ${c.gst ? 'checked' : ''}> GST Certificate</label>
        `;
    } else if (mod.id === 'liveness') {
        html += `
            <label class="config-label"><input type="radio" name="cfg-live-mode" value="eye_tracking" ${c.mode === 'eye_tracking' ? 'checked' : ''}> Eye Tracking</label>
            <label class="config-label"><input type="radio" name="cfg-live-mode" value="audio_guided" ${c.mode === 'audio_guided' ? 'checked' : ''}> Audio Guided</label>
            <label class="config-label"><input type="radio" name="cfg-live-mode" value="video" ${c.mode === 'video' ? 'checked' : ''}> Passive Video</label>
        `;
    } else if (mod.id === 'cross_match') {
        html += `
            <label class="config-label"><input type="checkbox" id="cfg-match-face" ${c.match_face ? 'checked' : ''}> Match Face (ID vs Selfie)</label>
            <label class="config-label"><input type="checkbox" id="cfg-match-name" ${c.match_name ? 'checked' : ''}> Match Name (ID vs Profile)</label>
        `;
    } else if (mod.id === 'fraud_analysis') {
        html += `
            <label class="config-label"><input type="checkbox" id="cfg-deep-scan" ${c.deep_scan ? 'checked' : ''}> Deep Scan (Tampering)</label>
            <label class="config-label"><input type="checkbox" id="cfg-synthetic" ${c.synthetic_check ? 'checked' : ''}> Synthetic Media Check (Deepfake)</label>
        `;
    }
    
    html += '</div>';
    configFormContainer.innerHTML = html;
    configModal.style.display = 'flex';
}

cancelConfigBtn.addEventListener('click', () => {
    configModal.style.display = 'none';
    currentConfigModuleId = null;
});

saveConfigBtn.addEventListener('click', () => {
    if (!currentConfigModuleId) return;
    const mod = pipeline.find(m => m.uniqueId === currentConfigModuleId);
    if (!mod) return;
    
    if (mod.id === 'ocr') {
        mod.config = {
            aadhaar: document.getElementById('cfg-aadhaar').checked,
            pan: document.getElementById('cfg-pan').checked,
            passport: document.getElementById('cfg-passport').checked,
            company: document.getElementById('cfg-company').checked,
            gst: document.getElementById('cfg-gst').checked
        };
    } else if (mod.id === 'liveness') {
        mod.config = {
            mode: document.querySelector('input[name="cfg-live-mode"]:checked').value
        };
    } else if (mod.id === 'cross_match') {
        mod.config = {
            match_face: document.getElementById('cfg-match-face').checked,
            match_name: document.getElementById('cfg-match-name').checked
        };
    } else if (mod.id === 'fraud_analysis') {
        mod.config = {
            deep_scan: document.getElementById('cfg-deep-scan').checked,
            synthetic_check: document.getElementById('cfg-synthetic').checked
        };
    }
    
    configModal.style.display = 'none';
    currentConfigModuleId = null;
});

// Generate Link
generateBtn.addEventListener('click', () => {
    generateBtn.textContent = 'Generating...';
    generateBtn.disabled = true;

    setTimeout(() => {
        const uuid = crypto.randomUUID ? crypto.randomUUID() : 'req-' + Date.now();
        const link = `https://verify.verifyyy.com/session?id=${uuid}`;
        
        // Save pipeline config to localStorage for the preview session
        localStorage.setItem(`pipeline_${uuid}`, JSON.stringify(pipeline));
        
        generatedLinkEl.textContent = link;
        previewBtn.dataset.uuid = uuid;
        modal.style.display = 'flex';
        
        generateBtn.textContent = 'Generate Link';
        generateBtn.disabled = false;
    }, 800);
});

// Modal Actions
closeModalBtn.addEventListener('click', () => {
    modal.style.display = 'none';
});

previewBtn.addEventListener('click', () => {
    const uuid = previewBtn.dataset.uuid;
    window.open(`verify-session.html?id=${uuid}`, '_blank');
});

copyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(generatedLinkEl.textContent).then(() => {
        const originalText = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        setTimeout(() => {
            copyBtn.textContent = originalText;
        }, 2000);
    });
});

// Initialize
renderAvailableModules();
renderPipeline();
