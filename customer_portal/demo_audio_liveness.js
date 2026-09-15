// Audio Liveness Constants
const AUDIO_YAW_THRESHOLD = 0.10;
const AUDIO_TURN_TIMEOUT_MS = 14000;
const AUDIO_BLINK_TARGET = 2;
const AUDIO_BLINK_TIMEOUT_MS = 14000;
const BLINK_EAR_DROP = 0.045; // Threshold for blink

let faceMeshModel = null;
let currentLandmarks = null;
let audioCtx = null;
let isProcessing = false;
let cameraStream = null;

// Speech Synthesis
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

// Chimes for blind users
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
        setTimeout(() => { osc.stop(); }, durationMs);
    } catch (e) {
        console.warn("AudioContext error", e);
    }
}

const chime = {
    ok: () => playTone(880, 180),
    fail: () => playTone(220, 300),
    next: () => playTone(560, 120),
};

// UI Helpers
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

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Face Mesh Initialization
async function initFaceMesh() {
    if (faceMeshModel) return;

    faceMeshModel = new FaceMesh({
        locateFile: (file) => `mediapipe/face_mesh/${file}`,
    });

    faceMeshModel.setOptions({ 
        maxNumFaces: 1, 
        refineLandmarks: true, 
        minDetectionConfidence: 0.5, 
        minTrackingConfidence: 0.5 
    });

    faceMeshModel.onResults((results) => {
        if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
            currentLandmarks = results.multiFaceLandmarks[0];
        } else {
            currentLandmarks = null;
        }
    });

    // Start video loop
    const videoElement = document.getElementById('hiddenVideo');
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
    videoElement.srcObject = cameraStream;
    
    // Play video to start processing frames
    await videoElement.play();

    isProcessing = true;
    processVideoFrame(videoElement);
}

async function processVideoFrame(videoElement) {
    if (!isProcessing) return;
    
    // We send every frame to FaceMesh
    if (videoElement.videoWidth > 0 && videoElement.videoHeight > 0) {
        await faceMeshModel.send({ image: videoElement });
    }
    
    requestAnimationFrame(() => processVideoFrame(videoElement));
}

// Geometric calculations
function currentYaw() {
    if (!currentLandmarks || currentLandmarks.length < 468) return null;
    const lm = currentLandmarks;
    const nose = lm[1];
    const lOuter = lm[33];
    const rOuter = lm[263];
    if (!nose || !lOuter || !rOuter) return null;

    const midEyeX = (lOuter.x + rOuter.x) / 2;
    const iod = Math.max(1e-4, Math.hypot(rOuter.x - lOuter.x, rOuter.y - lOuter.y));
    const eyeYaw = (nose.x - midEyeX) / iod;

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

function calculateEAR(eyeLandmarks) {
    const v1 = Math.hypot(eyeLandmarks[1].x - eyeLandmarks[5].x, eyeLandmarks[1].y - eyeLandmarks[5].y);
    const v2 = Math.hypot(eyeLandmarks[2].x - eyeLandmarks[4].x, eyeLandmarks[2].y - eyeLandmarks[4].y);
    const h = Math.hypot(eyeLandmarks[0].x - eyeLandmarks[3].x, eyeLandmarks[0].y - eyeLandmarks[3].y);
    return (v1 + v2) / (2.0 * Math.max(h, 1e-6));
}

function currentEar() {
    if (!currentLandmarks || currentLandmarks.length < 468) return null;
    
    const leftEyeIdx = [33, 160, 158, 133, 153, 144];
    const rightEyeIdx = [362, 385, 387, 263, 373, 380];
    
    const leftEye = leftEyeIdx.map(i => currentLandmarks[i]);
    const rightEye = rightEyeIdx.map(i => currentLandmarks[i]);
    
    const leftEar = calculateEAR(leftEye);
    const rightEar = calculateEAR(rightEye);
    
    return (leftEar + rightEar) / 2.0;
}

// Logic primitives
async function measureBaselineYaw(durationMs = 700) {
    const samples = [];
    const t0 = performance.now();
    while (performance.now() - t0 < durationMs) {
        const y = currentYaw();
        if (y != null && Number.isFinite(y)) samples.push(y);
        await wait(30);
    }
    return samples.length > 0 ? samples.reduce((a, b) => a + b, 0) / samples.length : (currentYaw() ?? 0);
}

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
                    if (Math.abs(delta) >= AUDIO_YAW_THRESHOLD && (forbidSign === 0 || sign !== forbidSign)) {
                        turned = true;
                        peak = Math.abs(delta);
                        peakSign = sign;
                        chime.next();
                        announce('Good turn detected! Now return to the centre.', 'Turn detected — Face forward');
                        speak('Good. Now face forward again.');
                    }
                } else {
                    if (Math.abs(delta) > peak) peak = Math.abs(delta);
                    if (Math.abs(delta) <= AUDIO_YAW_THRESHOLD * 0.50) {
                        resolve({ ok: true, sign: peakSign, peak });
                        return;
                    }
                }
            }

            if (performance.now() - t0 >= timeoutMs) {
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

async function measureOpenEar(durationMs = 700) {
    const samples = [];
    const t0 = performance.now();
    while (performance.now() - t0 < durationMs) {
        const ear = currentEar();
        if (ear != null) samples.push(ear);
        await wait(40);
    }
    return samples.length ? samples.reduce((a, b) => a + b, 0) / samples.length : 0.25;
}

function waitForBlinks(openEar, count, timeoutMs) {
    return new Promise((resolve) => {
        const threshold = Math.max(0.12, openEar - BLINK_EAR_DROP);
        const t0 = performance.now();
        let closed = false;
        let blinks = 0;

        const tick = () => {
            const ear = currentEar();
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

function waitForFace(timeoutMs) {
    return new Promise((resolve) => {
        const t0 = performance.now();
        const tick = () => {
            if (currentLandmarks) {
                resolve(true);
                return;
            }
            if (performance.now() - t0 >= timeoutMs) {
                resolve(false);
                return;
            }
            requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    });
}


// Main Pipeline
async function startAudioLiveness() {
    const btn = document.getElementById('start-btn');
    const loadingMsg = document.getElementById('loading-msg');
    const overlay = document.getElementById('audioOverlay');
    
    btn.classList.add('hidden');
    loadingMsg.classList.remove('hidden');

    try {
        await initFaceMesh();
    } catch (e) {
        console.error("Camera/Model init failed", e);
        loadingMsg.textContent = "Error: Failed to access camera or models.";
        btn.classList.remove('hidden');
        return;
    }

    document.getElementById('intro-card').classList.add('hidden');
    overlay.classList.remove('hidden');

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
        await wait(2000);

        const faceFound = await waitForFace(10000);
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

        // Measure baseline
        const baseline1 = await measureBaselineYaw(800);

        // Turn 1
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

        // Re-center
        announce('Face forward for the next check.', 'Centering…');
        const baseline2 = await measureBaselineYaw(500);

        // Turn 2
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
        
        renderAudioSteps(3, checks[3].passed ? 3 : 2, -1);

        const passedCount = checks.filter(c => c.passed).length;
        let verdict = 'NOT_CONFIRMED';
        if (checks[0].passed && checks[3].passed && (checks[1].passed || checks[2].passed)) verdict = 'REAL_PERSON';
        else if (checks[0].passed && (checks[3].passed || checks[1].passed || checks[2].passed)) verdict = 'LIKELY_REAL';

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
        
        showResults(verdict, checks, Math.round((passedCount / checks.length) * 100));

    } catch (err) {
        console.error("Pipeline Error", err);
    } finally {
        stopSpeech();
        isProcessing = false;
        if (cameraStream) {
            cameraStream.getTracks().forEach(t => t.stop());
        }
    }
}

function showResults(verdict, checks, confidence) {
    document.getElementById('audioOverlay').classList.add('hidden');
    const res = document.getElementById('resultsOverlay');
    res.classList.remove('hidden');

    const vt = document.getElementById('verdictTitle');
    vt.textContent = verdict === 'REAL_PERSON' ? '✅ Live Person Verified' : 
                     verdict === 'LIKELY_REAL' ? '⚠️ Likely Real (Partial)' : 
                     '❌ Verification Failed';
    vt.style.color = verdict === 'REAL_PERSON' ? '#10b981' : 
                     verdict === 'LIKELY_REAL' ? '#f59e0b' : '#ef4444';

    document.getElementById('confidenceText').textContent = `Confidence: ${confidence}% | Audio-Guided FaceMesh Tracker`;

    const list = document.getElementById('checksList');
    list.innerHTML = checks.map(c => `
        <div style="display:flex; justify-content:space-between; margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px;">
            <span style="color: ${c.passed ? '#cbd5e1' : '#ef4444'}">${c.label}</span>
            <span>${c.passed ? '✅ Pass' : '❌ Fail'}</span>
        </div>
    `).join('');
}
