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
        webgazer.params.dataTimestep = 16; // ~60Hz high sampling rate for smooth movement
        webgazer.params.applyKalmanFilter = true; // Built-in Kalman filter for smoother predictions
        
        await webgazer.setRegression('weightedRidge') // weightedRidge gives more accurate predictions
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
        const REQUIRED_HOVER_TIME = 2500; // 2.5s per dot for richer calibration data
        const SAMPLE_INTERVAL = 50; // Sample every 50ms = 50 samples per dot
        
        btn.addEventListener('mouseenter', () => {
            if (btn.classList.contains('cal-done')) return;
            
            hoverInterval = setInterval(() => {
                hoverTime += SAMPLE_INTERVAL;
                // Record both click and move events for richer training data
                webgazer.recordScreenPosition(x, y, 'click');
                webgazer.recordScreenPosition(x, y, 'move');
                
                // Visual feedback
                btn.style.opacity = Math.max(0.2, 1 - (hoverTime / REQUIRED_HOVER_TIME));
                
                if (hoverTime >= REQUIRED_HOVER_TIME) {
                    clearInterval(hoverInterval);
                    btn.classList.add('cal-done');
                    btn.style.opacity = '1';
                    checkCalibrationComplete();
                }
            }, SAMPLE_INTERVAL);
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

let targetGazeX = window.innerWidth / 2;
let targetGazeY = window.innerHeight / 2;
let currentReticleX = window.innerWidth / 2;
let currentReticleY = window.innerHeight / 2;
let hasReceivedGaze = false;
let reticleRenderStarted = false;

function finishCalibration() {
    calibrationFinished = true;
    document.getElementById('calOverlay').classList.add('hidden');
    
    // Hide video feed to focus on tracking
    const vidContainer = document.getElementById('webgazerVideoContainer');
    if (vidContainer) vidContainer.style.display = 'none';
    
    // Show reticle
    const reticle = document.getElementById('gazeReticle');
    reticle.style.display = 'block';
    
    // Start listening for gaze predictions directly
    webgazer.setGazeListener((data, elapsedTime) => {
        if (!data || !calibrationFinished) return;
        if (typeof data.x === 'number' && typeof data.y === 'number' && !isNaN(data.x) && !isNaN(data.y)) {
            targetGazeX = data.x;
            targetGazeY = data.y;
            if (!hasReceivedGaze) {
                currentReticleX = data.x;
                currentReticleY = data.y;
                hasReceivedGaze = true;
            }
        }
    });

    // Start 60fps buttery-smooth reticle interpolation
    if (!reticleRenderStarted) {
        reticleRenderStarted = true;
        const animateReticle = () => {
            if (calibrationFinished) {
                // Responsive smoothing: 0.35 factor ensures rapid, smooth response without lag
                currentReticleX += (targetGazeX - currentReticleX) * 0.35;
                currentReticleY += (targetGazeY - currentReticleY) * 0.35;
                reticle.style.transform = `translate3d(${currentReticleX}px, ${currentReticleY}px, 0) translate(-50%, -50%)`;
            }
            requestAnimationFrame(animateReticle);
        };
        requestAnimationFrame(animateReticle);
    }

    // Run verification challenge
    startChallenge();
}

function getComfortableDotPosition(index) {
    // 4 distinct comfortable quadrants with safe margins away from screen borders
    const positions = [
        { x: 0.32, y: 0.35 },
        { x: 0.68, y: 0.35 },
        { x: 0.32, y: 0.65 },
        { x: 0.68, y: 0.65 }
    ];
    const base = positions[index % positions.length];
    const jitterX = (Math.random() - 0.5) * 0.08;
    const jitterY = (Math.random() - 0.5) * 0.08;
    return {
        x: (base.x + jitterX) * window.innerWidth,
        y: (base.y + jitterY) * window.innerHeight
    };
}

async function startChallenge() {
    const TOTAL_DOTS = 4;
    const CHALLENGE_DURATION_MS = 4000; // Exactly 4.0 seconds per target dot
    const REQUIRED_IN_RADIUS_MS = 1000; // 1.0 second total within the radius confirms valid tracking
    
    // Target radius decreased by 1/4th (75% of previous size)
    const TARGET_RADIUS = Math.round(Math.max(190, Math.min(window.innerWidth, window.innerHeight) * 0.24) * 0.75);
    
    const challengeHud = document.getElementById('challengeHud');
    const challengeStepTitle = document.getElementById('challengeStepTitle');
    const challengeTimer = document.getElementById('challengeTimer');
    const reticle = document.getElementById('gazeReticle');
    
    challengeHud.classList.remove('hidden');

    // Create the visual radius zone (circular dashed boundary)
    const radiusZone = document.createElement('div');
    radiusZone.id = 'targetRadiusZone';
    radiusZone.style.position = 'fixed';
    radiusZone.style.width = `${TARGET_RADIUS * 2}px`;
    radiusZone.style.height = `${TARGET_RADIUS * 2}px`;
    radiusZone.style.borderRadius = '50%';
    radiusZone.style.border = '2px dashed rgba(45, 212, 191, 0.4)';
    radiusZone.style.backgroundColor = 'rgba(45, 212, 191, 0.05)';
    radiusZone.style.pointerEvents = 'none';
    radiusZone.style.zIndex = '9997';
    radiusZone.style.transform = 'translate(-50%, -50%)';
    radiusZone.style.transition = 'border-color 0.2s, background-color 0.2s';
    document.body.appendChild(radiusZone);

    // Create the center target dot
    const target = document.createElement('div');
    target.id = 'challengeTargetDot';
    target.style.position = 'fixed';
    target.style.width = '48px';
    target.style.height = '48px';
    target.style.backgroundColor = '#f59e0b';
    target.style.borderRadius = '50%';
    target.style.zIndex = '9998';
    target.style.pointerEvents = 'none';
    target.style.transform = 'translate(-50%, -50%)';
    target.style.boxShadow = '0 0 20px rgba(245, 158, 11, 0.6)';
    target.style.transition = 'background-color 0.2s, box-shadow 0.2s';
    document.body.appendChild(target);

    let dotsPassed = 0;

    for (let i = 0; i < TOTAL_DOTS; i++) {
        const pos = getComfortableDotPosition(i);
        
        // Position target dot & radius circle
        target.style.left = `${pos.x}px`;
        target.style.top = `${pos.y}px`;
        target.style.backgroundColor = '#f59e0b';
        target.style.boxShadow = '0 0 20px rgba(245, 158, 11, 0.6)';

        radiusZone.style.left = `${pos.x}px`;
        radiusZone.style.top = `${pos.y}px`;
        radiusZone.style.borderColor = 'rgba(45, 212, 191, 0.4)';
        radiusZone.style.backgroundColor = 'rgba(45, 212, 191, 0.05)';

        challengeStepTitle.textContent = `Follow the Target Dot (${i + 1} / ${TOTAL_DOTS})`;
        challengeTimer.textContent = '4.0s';
        reticle.classList.remove('in-radius');

        // Settle delay: 0.8 seconds to look at the new dot position
        await new Promise(r => setTimeout(r, 800));

        // Track gaze for exactly 4.0 seconds
        const dotSuccess = await new Promise((resolve) => {
            const startTime = performance.now();
            let accumulatedInRadiusMs = 0;
            let lastTick = startTime;

            const tick = (now) => {
                const dt = now - lastTick;
                lastTick = now;
                const elapsed = now - startTime;
                const remaining = Math.max(0, (CHALLENGE_DURATION_MS - elapsed) / 1000);
                challengeTimer.textContent = `${remaining.toFixed(1)}s`;

                // Calculate distance from current gaze reticle position to target center
                const distToTarget = Math.hypot(currentReticleX - pos.x, currentReticleY - pos.y);
                const insideRadius = distToTarget <= TARGET_RADIUS;

                if (insideRadius) {
                    accumulatedInRadiusMs += dt;
                    radiusZone.style.borderColor = 'rgba(16, 185, 129, 0.8)';
                    radiusZone.style.backgroundColor = 'rgba(16, 185, 129, 0.15)';
                    target.style.backgroundColor = '#10b981';
                    target.style.boxShadow = '0 0 25px rgba(16, 185, 129, 0.8)';
                    reticle.classList.add('in-radius');
                } else {
                    radiusZone.style.borderColor = 'rgba(45, 212, 191, 0.4)';
                    radiusZone.style.backgroundColor = 'rgba(45, 212, 191, 0.05)';
                    target.style.backgroundColor = '#f59e0b';
                    target.style.boxShadow = '0 0 20px rgba(245, 158, 11, 0.6)';
                    reticle.classList.remove('in-radius');
                }

                if (elapsed >= CHALLENGE_DURATION_MS) {
                    // Valid if pupil spent at least REQUIRED_IN_RADIUS_MS inside the target radius
                    const passed = accumulatedInRadiusMs >= REQUIRED_IN_RADIUS_MS;
                    resolve(passed);
                    return;
                }

                requestAnimationFrame(tick);
            };

            requestAnimationFrame(tick);
        });

        if (dotSuccess) {
            dotsPassed++;
        }
    }

    // Clean up UI elements
    radiusZone.remove();
    target.remove();
    challengeHud.classList.add('hidden');
    reticle.style.display = 'none';
    reticle.classList.remove('in-radius');

    // Evaluate result: at least 50% (2 of 4) passed confirms live human eye movement
    const accuracy = dotsPassed / TOTAL_DOTS;
    showVerdict(accuracy, dotsPassed, TOTAL_DOTS);
}

function showVerdict(accuracy, dotsPassed, totalDots) {
    webgazer.pause();
    const overlay = document.getElementById('challengeOverlay');
    const title = document.getElementById('verdict-title');
    const text = document.getElementById('verdict-text');
    
    overlay.classList.remove('hidden');
    
    if (accuracy >= 0.5) {
        title.textContent = '✅ Liveness Confirmed';
        title.style.color = '#10b981';
        text.textContent = `Eye tracking liveness verified (${dotsPassed} of ${totalDots} targets tracked successfully - ${Math.round(accuracy * 100)}%). A real person is present.`;
    } else {
        title.textContent = '❌ Verification Failed';
        title.style.color = '#ef4444';
        text.textContent = `Tracking accuracy insufficient (${dotsPassed} of ${totalDots} targets inside radius - ${Math.round(accuracy * 100)}%). Please keep your face steady and try again.`;
    }
}
