document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('id');
    
    const wrapper = document.getElementById('steps-wrapper');
    const loadingStep = document.getElementById('step-loading');
    const errorStep = document.getElementById('step-error');
    const finalStep = document.getElementById('step-final');
    const progressBar = document.getElementById('progress-bar');
    const progressFill = document.getElementById('progress-fill');
    const resultBox = document.getElementById('result-box');

    let pipelineConfig = [];
    let currentStepIndex = 0;
    let results = {};

    // 1. Initialize and Validate Session
    setTimeout(() => {
        loadingStep.classList.remove('active');
        
        if (!sessionId) {
            errorStep.classList.add('active');
            return;
        }

        const savedConfig = localStorage.getItem(`pipeline_${sessionId}`);
        if (!savedConfig) {
            errorStep.querySelector('p').textContent = "Pipeline configuration not found. Session expired or invalid.";
            errorStep.classList.add('active');
            return;
        }

        pipelineConfig = JSON.parse(savedConfig);
        
        if (pipelineConfig.length === 0) {
            errorStep.querySelector('p').textContent = "Pipeline has no active modules configured.";
            errorStep.classList.add('active');
            return;
        }

        // Initialize UI
        progressBar.style.display = 'block';
        createStepElements();
        showCurrentStep();

    }, 1500); // Simulate network latency

    // 2. Create UI for each pipeline module
    function createStepElements() {
        pipelineConfig.forEach((mod, index) => {
            const stepDiv = document.createElement('div');
            stepDiv.className = 'step-container';
            stepDiv.id = `step-module-${index}`;
            
            let icon = '🛡️';
            let actionText = 'Process Data';
            let title = mod.name;

            if (mod.id === 'ocr') {
                icon = '📄';
                actionText = 'Upload Document Front & Back';
            } else if (mod.id === 'liveness') {
                icon = '👤';
                actionText = 'Start Camera & Record Face';
            } else if (mod.id === 'cross_match') {
                icon = '🔄';
                actionText = 'Run AI Matching';
            } else if (mod.id === 'fraud_analysis') {
                icon = '🔍';
                actionText = 'Scan for Deepfakes & Tampering';
            }

            stepDiv.innerHTML = `
                <div class="step-icon">${icon}</div>
                <h3>${title}</h3>
                <p style="color: var(--text-muted);">${mod.desc}</p>
                
                <div class="upload-area" onclick="simulateModuleProcess(${index}, '${mod.id}')">
                    <div id="action-content-${index}">
                        <div style="font-size: 2rem; margin-bottom: 8px;">➕</div>
                        <strong>${actionText}</strong>
                        <p style="font-size: 0.8rem; margin: 4px 0 0; color: var(--text-muted);">Click to simulate data capture</p>
                    </div>
                    <div id="loader-content-${index}" style="display: none;">
                        <div class="loader" style="width: 30px; height: 30px; border-width: 3px; margin-bottom: 16px;"></div>
                        <strong>Processing locally...</strong>
                    </div>
                </div>
            `;
            wrapper.insertBefore(stepDiv, finalStep);
        });
    }

    // 3. Navigation
    function showCurrentStep() {
        // Hide all dynamically generated steps
        pipelineConfig.forEach((_, index) => {
            document.getElementById(`step-module-${index}`).classList.remove('active');
        });
        
        if (currentStepIndex < pipelineConfig.length) {
            document.getElementById(`step-module-${currentStepIndex}`).classList.add('active');
            
            // Update progress bar
            const percent = (currentStepIndex / pipelineConfig.length) * 100;
            progressFill.style.width = `${percent}%`;
        } else {
            // Finished all steps
            progressFill.style.width = `100%`;
            showFinalResults();
        }
    }

    // 4. Simulate Processing
    window.simulateModuleProcess = function(index, modId) {
        if (index !== currentStepIndex) return;

        const actionContent = document.getElementById(`action-content-${index}`);
        const loaderContent = document.getElementById(`loader-content-${index}`);
        const uploadArea = actionContent.parentElement;

        actionContent.style.display = 'none';
        loaderContent.style.display = 'block';
        uploadArea.style.pointerEvents = 'none';

        setTimeout(() => {
            // Generate mock result based on module
            if (modId === 'ocr') {
                results.Document_OCR = { status: 'Verified', documentType: 'National ID', confidence: '99.2%' };
            } else if (modId === 'liveness') {
                results.Liveness_Check = { status: 'Passed', spoofScore: '0.01', live: true };
            } else if (modId === 'cross_match') {
                results.Cross_Match = { status: 'Matched', similarityScore: '98.5%' };
            } else if (modId === 'fraud_analysis') {
                results.Fraud_Analysis = { status: 'Clear', deepfakeDetected: false, tamperingDetected: false };
            }

            currentStepIndex++;
            showCurrentStep();
        }, 2000); // Simulate 2 seconds of AI processing
    };

    // 5. Show Final Result
    function showFinalResults() {
        finalStep.classList.add('active');
        
        const resultJSON = JSON.stringify(results, null, 2);
        resultBox.innerHTML = `<pre style="margin:0;">${resultJSON}</pre>`;
    }
});
