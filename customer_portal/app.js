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
    pipeline.push({ ...mod, uniqueId: Date.now() + Math.random() });
    renderPipeline();
}

// Remove from Pipeline
function removeModule(uniqueId) {
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
            node.innerHTML = `
                <h4>${index + 1}. ${mod.name}</h4>
                <button class="remove-node" onclick="removeModule(${mod.uniqueId})">&times;</button>
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
