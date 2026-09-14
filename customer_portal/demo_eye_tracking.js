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
    const btn = document.getElementById('btn-start-demo');
    const loadingMsg = document.getElementById('loading-msg');
    
    btn.classList.add('hidden');
    loadingMsg.classList.remove('hidden');
    
    try {
        // Initialize WebGazer
        webgazer.params.showVideoPreview = false;
        webgazer.params.showFaceOverlay = false;
        webgazer.params.showFaceFeedbackBox = false;
        webgazer.params.showGazeDot = false; // We use our own reticle after calibration
        
        await webgazer.setRegression('ridge')
            .setTracker('TFFacemesh')
            .begin();

        document.getElementById('intro-card').classList.add('hidden');

        // Ensure the video container is hidden so it doesn't block dots
        const vidContainer = document.getElementById('webgazerVideoContainer');
        if (vidContainer) {
            vidContainer.style.display = 'none';
        }

        startCalibration();
    } catch (err) {
        loadingMsg.textContent = "Error: Failed to start camera or AI models. Please ensure camera permissions are allowed.";
        loadingMsg.style.color = '#ef4444';
        btn.classList.remove('hidden');
        console.error("WebGazer start error:", err);
    }
}

function startCalibration() {
    document.getElementById('calOverlay').classList.remove('hidden');
    const calLayer = document.getElementById('calLayer');
    calLayer.innerHTML = '';
    
    // WebGazer by default adds mouse tracking listeners for clicks and moves.
    // We can rely on our explicit recordings during hover.
    webgazer.removeMouseEventListeners();
    
    CAL_DOTS.forEach(dot => {
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
        
        let hoverInterval;
        let hoverTime = 0;
        const REQUIRED_HOVER_TIME = 1500; // 1.5s per dot
        
        btn.addEventListener('mouseenter', () => {
            if (btn.classList.contains('cal-done')) return;
            
            hoverInterval = setInterval(() => {
                hoverTime += 100;
                // Force a recording of this point
                webgazer.recordScreenPosition(x, y, 'click');
                
                // Visual feedback
                btn.style.opacity = Math.max(0.2, 1 - (hoverTime / REQUIRED_HOVER_TIME));
                
                if (hoverTime >= REQUIRED_HOVER_TIME) {
                    clearInterval(hoverInterval);
                    btn.classList.add('cal-done');
                    btn.style.opacity = '1';
                    checkCalibrationComplete();
                }
            }, 100);
        });
        
        btn.addEventListener('mouseleave', () => {
            if (hoverInterval) clearInterval(hoverInterval);
            if (!btn.classList.contains('cal-done')) {
                hoverTime = 0;
                btn.style.opacity = '1';
            }
        });
        
        calLayer.appendChild(btn);
    });
}

function checkCalibrationComplete() {
    const doneElements = document.querySelectorAll('.cal-done');
    const done = doneElements.length;
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
    let dotsHit = 0;
    let currentDotIndex = 0;
    const TOTAL_DOTS = 4;
    const TARGET_RADIUS = 250; // Comfortable generous radius
    
    const target = document.createElement('div');
    target.style.position = 'fixed';
    target.style.width = '60px';
    target.style.height = '60px';
    target.style.backgroundColor = '#f59e0b';
    target.style.borderRadius = '50%';
    target.style.zIndex = '9998';
    target.style.boxShadow = '0 0 15px rgba(245, 158, 11, 0.6)';
    document.body.appendChild(target);

    let challengeInterval = null;
    let dotTimeout = null;

    function showNextDot() {
        if (currentDotIndex >= TOTAL_DOTS) {
            endChallenge();
            return;
        }

        // Generate random position (keep it somewhat centralized to avoid edges)
        const margin = 100;
        const x = margin + Math.random() * (window.innerWidth - 2 * margin);
        const y = margin + Math.random() * (window.innerHeight - 2 * margin);
        
        target.style.left = `${x}px`;
        target.style.top = `${y}px`;
        target.style.transform = 'translate(-50%, -50%) scale(1)';
        target.style.backgroundColor = '#f59e0b';
        
        let lookDuration = 0;
        
        if (challengeInterval) clearInterval(challengeInterval);
        if (dotTimeout) clearTimeout(dotTimeout);
        
        challengeInterval = setInterval(() => {
            const pred = webgazer.getCurrentPrediction();
            if (pred) {
                const dist = Math.hypot(pred.x - x, pred.y - y);
                // If eye tracking meets inside our generous radius
                if (dist < TARGET_RADIUS) {
                    lookDuration += 50;
                    target.style.transform = 'translate(-50%, -50%) scale(1.2)';
                    target.style.backgroundColor = '#10b981'; // Turn green on hit
                    
                    // If they look at it inside the radius for 0.5s, it counts as a hit!
                    if (lookDuration > 500) {
                        dotsHit++;
                        currentDotIndex++;
                        showNextDot();
                    }
                } else {
                    lookDuration = 0;
                    target.style.transform = 'translate(-50%, -50%) scale(1)';
                    target.style.backgroundColor = '#f59e0b';
                }
            }
        }, 50);

        // Give them 3 seconds max per dot to find it
        dotTimeout = setTimeout(() => {
            currentDotIndex++;
            showNextDot();
        }, 3000);
    }

    function endChallenge() {
        if (challengeInterval) clearInterval(challengeInterval);
        if (dotTimeout) clearTimeout(dotTimeout);
        target.remove();
        document.getElementById('gazeReticle').style.display = 'none';
        
        const accuracy = dotsHit / TOTAL_DOTS;
        showVerdict(accuracy);
    }

    // Give user 1s before starting the first dot
    setTimeout(showNextDot, 1000);
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
