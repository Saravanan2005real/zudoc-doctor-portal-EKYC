const CAL_DOTS = [
    { id: 1, x: 0.1, y: 0.1 },
    { id: 2, x: 0.5, y: 0.1 },
    { id: 3, x: 0.9, y: 0.1 },
    { id: 4, x: 0.1, y: 0.5 },
    { id: 5, x: 0.5, y: 0.5 },
    { id: 6, x: 0.9, y: 0.5 },
    { id: 7, x: 0.1, y: 0.9 },
    { id: 8, x: 0.5, y: 0.9 },
    { id: 9, x: 0.9, y: 0.9 },
];

const clickCounts = {};
let calibrationFinished = false;

window.onload = function() {
    document.getElementById('btn-start-demo').addEventListener('click', startDemo);
};

async function startDemo() {
    document.getElementById('intro-card').classList.add('hidden');
    
    // Initialize WebGazer
    webgazer.params.showVideoPreview = true;
    webgazer.params.showFaceOverlay = true;
    webgazer.params.showFaceFeedbackBox = true;
    webgazer.params.showGazeDot = false; // We use our own reticle after calibration
    
    await webgazer.setRegression('ridge')
        .setTracker('TFFacemesh')
        .begin();

    // The video container is created by webgazer
    const vidContainer = document.getElementById('webgazerVideoContainer');
    if (vidContainer) {
        vidContainer.style.display = 'block';
    }

    startCalibration();
}

function startCalibration() {
    document.getElementById('calOverlay').classList.remove('hidden');
    const calLayer = document.getElementById('calLayer');
    calLayer.innerHTML = '';
    
    CAL_DOTS.forEach(dot => {
        clickCounts[dot.id] = 0;
        const btn = document.createElement('button');
        btn.className = 'cal-dot';
        btn.dataset.calId = dot.id;
        
        // Calculate px positions
        const padX = 20;
        const padY = 20;
        const x = padX + dot.x * (window.innerWidth - 2 * padX);
        const y = padY + dot.y * (window.innerHeight - 2 * padY);
        
        btn.style.left = `${x}px`;
        btn.style.top = `${y}px`;
        
        btn.addEventListener('click', (e) => {
            // WebGazer automatically calibrates on click globally if addMouseEventListeners is on (default).
            // But we manually force a record just in case.
            webgazer.recordScreenPosition(x, y, 'click');
            
            clickCounts[dot.id]++;
            
            // Give visual feedback
            btn.style.opacity = Math.max(0.2, 1 - (clickCounts[dot.id] / 3));
            
            if (clickCounts[dot.id] >= 3) {
                btn.classList.add('cal-done');
                btn.style.opacity = '1';
                checkCalibrationComplete();
            }
        });
        
        calLayer.appendChild(btn);
    });
}

function checkCalibrationComplete() {
    const done = CAL_DOTS.filter(d => clickCounts[d.id] >= 3).length;
    document.getElementById('calProgress').textContent = `${done} / ${CAL_DOTS.length} dots`;
    
    if (done === CAL_DOTS.length) {
        finishCalibration();
    }
}

function finishCalibration() {
    calibrationFinished = true;
    document.getElementById('calOverlay').classList.add('hidden');
    
    // Hide video feed to focus on tracking
    const vidContainer = document.getElementById('webgazerVideoContainer');
    if (vidContainer) vidContainer.style.display = 'none';
    
    // Show reticle
    const reticle = document.getElementById('gazeReticle');
    reticle.style.display = 'block';
    
    // Start listening for gaze
    webgazer.setGazeListener((data, elapsedTime) => {
        if (!data || !calibrationFinished) return;
        
        reticle.style.left = `${data.x}px`;
        reticle.style.top = `${data.y}px`;
    });

    // Run verification challenge
    startChallenge();
}

function startChallenge() {
    // Simply show a target in the center for 3 seconds and measure if gaze is close
    const target = document.createElement('div');
    target.style.position = 'fixed';
    target.style.top = '50%';
    target.style.left = '50%';
    target.style.transform = 'translate(-50%, -50%)';
    target.style.width = '60px';
    target.style.height = '60px';
    target.style.backgroundColor = '#f59e0b';
    target.style.borderRadius = '50%';
    target.style.zIndex = '9998';
    target.style.boxShadow = '0 0 15px rgba(245, 158, 11, 0.6)';
    document.body.appendChild(target);

    // Give user 1s to look at center, then measure for 2s
    let hits = 0;
    let total = 0;
    
    let challengeInterval = null;
    
    setTimeout(() => {
        challengeInterval = setInterval(() => {
            const pred = webgazer.getCurrentPrediction();
            if (pred) {
                total++;
                const cx = window.innerWidth / 2;
                const cy = window.innerHeight / 2;
                const dist = Math.hypot(pred.x - cx, pred.y - cy);
                
                // If within 150px of center, it's a hit
                if (dist < 150) {
                    hits++;
                    target.style.transform = 'translate(-50%, -50%) scale(1.2)';
                } else {
                    target.style.transform = 'translate(-50%, -50%) scale(1)';
                }
            }
        }, 50);
    }, 1000);

    // End after 3 seconds total
    setTimeout(() => {
        clearInterval(challengeInterval);
        target.remove();
        document.getElementById('gazeReticle').style.display = 'none';
        
        const accuracy = total > 0 ? (hits / total) : 0;
        showVerdict(accuracy);
    }, 4000);
}

function showVerdict(accuracy) {
    webgazer.pause();
    const overlay = document.getElementById('challengeOverlay');
    const title = document.getElementById('verdict-title');
    const text = document.getElementById('verdict-text');
    
    overlay.classList.remove('hidden');
    
    if (accuracy > 0.6) {
        title.textContent = '✅ Liveness Confirmed';
        title.style.color = '#10b981';
        text.textContent = `Excellent eye tracking accuracy (${Math.round(accuracy*100)}%). A real person is present.`;
    } else {
        title.textContent = '❌ Verification Failed';
        title.style.color = '#ef4444';
        text.textContent = `Poor tracking accuracy (${Math.round(accuracy*100)}%). Could not confirm liveness. Please try again.`;
    }
}
