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
        // Initialize WebGazer with all video preview and UI overlays disabled
        webgazer.params.showVideo = false;
        webgazer.params.showVideoPreview = false;
        webgazer.params.showFaceOverlay = false;
        webgazer.params.showFaceFeedbackBox = false;
        webgazer.params.showGazeDot = false; // We use our own reticle after calibration
        
        await webgazer.setRegression('ridge')
            .setTracker('TFFacemesh')
            .begin();

        // Enforce hiding of all WebGazer video and preview elements
        if (typeof webgazer.showVideoPreview === 'function') webgazer.showVideoPreview(false);
        if (typeof webgazer.showVideo === 'function') webgazer.showVideo(false);
        if (typeof webgazer.showFaceOverlay === 'function') webgazer.showFaceOverlay(false);
        if (typeof webgazer.showFaceFeedbackBox === 'function') webgazer.showFaceFeedbackBox(false);

        document.getElementById('intro-card').classList.add('hidden');

        // Ensure video container is sent completely offscreen and invisible
        const hideVidContainer = () => {
            const vidContainer = document.getElementById('webgazerVideoContainer');
            if (vidContainer) {
                vidContainer.style.setProperty('position', 'fixed', 'important');
                vidContainer.style.setProperty('top', '-9999px', 'important');
                vidContainer.style.setProperty('left', '-9999px', 'important');
                vidContainer.style.setProperty('opacity', '0', 'important');
                vidContainer.style.setProperty('visibility', 'hidden', 'important');
                vidContainer.style.setProperty('pointer-events', 'none', 'important');
                vidContainer.style.setProperty('border', 'none', 'important');
            }
        };
        hideVidContainer();
        setInterval(hideVidContainer, 500);

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

function randomDotPosition(index) {
  const zones = [{ x: 0.28, y: 0.32 }, { x: 0.72, y: 0.32 }, { x: 0.5, y: 0.5 }, { x: 0.28, y: 0.7 }, { x: 0.72, y: 0.7 }];
  const zone = zones[index % zones.length];
  const jitterX = (Math.random() - 0.5) * 0.12;
  const jitterY = (Math.random() - 0.5) * 0.1;
  return { 
      x: Math.min(0.85, Math.max(0.15, zone.x + jitterX)) * window.innerWidth, 
      y: Math.min(0.82, Math.max(0.22, zone.y + jitterY)) * window.innerHeight 
  };
}

function startChallenge() {
    const CHALLENGE_COUNT = 5;
    const CHALLENGE_DURATION_MS = 2000;
    const GAZE_HIT_RATIO = 0.6;
    
    const gazeHitRadius = () => Math.max(150, window.innerWidth * 0.1); 

    const target = document.createElement('div');
    target.style.position = 'fixed';
    target.style.width = '60px';
    target.style.height = '60px';
    target.style.backgroundColor = '#f59e0b';
    target.style.borderRadius = '50%';
    target.style.zIndex = '9998';
    target.style.boxShadow = '0 0 15px rgba(245, 158, 11, 0.6)';
    document.body.appendChild(target);

    let gazePasses = 0;
    
    async function runAllChallenges() {
        for (let i = 0; i < CHALLENGE_COUNT; i++) {
            const pos = randomDotPosition(i);
            target.style.left = `${pos.x}px`;
            target.style.top = `${pos.y}px`;
            target.style.transform = 'translate(-50%, -50%)';
            target.style.backgroundColor = '#f59e0b';
            
            // Wait 1 second to settle gaze
            await new Promise(r => setTimeout(r, 1000));
            
            // Run challenge and measure samples just like the doctor portal
            const passed = await new Promise((resolve) => {
                let hits = 0;
                let samples = 0;
                let sumDist = 0;
                const radius = gazeHitRadius();
                const t0 = performance.now();
                
                const tick = () => {
                    const elapsed = performance.now() - t0;
                    const pred = webgazer.getCurrentPrediction();
                    if (pred) {
                        samples++;
                        const d = Math.hypot(pred.x - pos.x, pred.y - pos.y);
                        sumDist += d;
                        if (d <= radius) {
                            hits++;
                            target.style.backgroundColor = '#10b981';
                        } else {
                            target.style.backgroundColor = '#f59e0b';
                        }
                    }
                    
                    if (elapsed >= CHALLENGE_DURATION_MS) {
                        const gazeRatio = samples ? hits / samples : 0;
                        const avgDist = samples ? sumDist / samples : Infinity;
                        
                        // Exact mathematical logic from doctor portal (gazeOk)
                        const gazeOk = samples >= 8 && (gazeRatio >= GAZE_HIT_RATIO || avgDist <= radius * 1.15);
                        resolve(gazeOk);
                        return;
                    }
                    requestAnimationFrame(tick);
                };
                requestAnimationFrame(tick);
            });
            
            if (passed) gazePasses++;
        }
        
        target.remove();
        document.getElementById('gazeReticle').style.display = 'none';
        
        // Doctor portal checks if you pass at least 60% of the challenges
        const accuracy = gazePasses / CHALLENGE_COUNT;
        showVerdict(accuracy);
    }
    
    runAllChallenges();
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
