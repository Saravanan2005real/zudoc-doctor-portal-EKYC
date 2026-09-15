// Audio Liveness Constants
const AUDIO_YAW_THRESHOLD = 0.15;
const AUDIO_PITCH_THRESHOLD = 0.12;
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
        const cheekYaw = (dLeft - dRight) / Math.max(1e-4, dRight + dLeft);
        const combined = 0.5 * eyeYaw + 0.5 * cheekYaw;
        return Number.isFinite(combined) ? combined : eyeYaw;
    }
    return Number.isFinite(eyeYaw) ? eyeYaw : null;
}

function currentPitch() {
    if (!currentLandmarks || currentLandmarks.length < 468) return null;
    const lm = currentLandmarks;
    const nose = lm[1];
    const lOuter = lm[33];
    const rOuter = lm[263];
    const mouthTop = lm[13];
    if (!nose || !lOuter || !rOuter || !mouthTop) return null;

    const midEyeY = (lOuter.y + rOuter.y) / 2;
    // vertical distance between eyes and mouth
    const eyeToMouth = Math.max(1e-4, mouthTop.y - midEyeY);
    const eyeToNose = nose.y - midEyeY;
    
    // Ratio of nose position relative to eyes and mouth. 
    // Looking down: nose moves closer to mouth (ratio increases). 
    // Looking up: nose moves closer to eyes (ratio decreases).
    const pitch = eyeToNose / eyeToMouth;
    return Number.isFinite(pitch) ? pitch : null;
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

async function measureBaselinePitch(durationMs = 700) {
    const samples = [];
    const t0 = performance.now();
    while (performance.now() - t0 < durationMs) {
        const p = currentPitch();
        if (p != null && Number.isFinite(p)) samples.push(p);
        await wait(30);
    }
    return samples.length > 0 ? samples.reduce((a, b) => a + b, 0) / samples.length : (currentPitch() ?? 0.5);
}

function waitForSpecificTurn(direction, baselineYaw, baselinePitch, timeoutMs) {
    return new Promise((resolve) => {
        const t0 = performance.now();
        let turned = false;
        let peakValue = 0;
        let turnHoldFrames = 0;
        let returnHoldFrames = 0;

        const tick = () => {
            const yaw = currentYaw();
            const pitch = currentPitch();
            if (yaw != null && pitch != null) {
                const deltaYaw = yaw - baselineYaw;
                const deltaPitch = pitch - baselinePitch;

                let isTurned = false;
                let isReturned = false;
                let currentVal = 0;

                // For strict checking, we ensure they only turn the requested way
                if (direction === 'left') {
                    // nose.x increases as user turns to their physical left (right side of camera image)
                    isTurned = deltaYaw > AUDIO_YAW_THRESHOLD;
                    isReturned = Math.abs(deltaYaw) <= AUDIO_YAW_THRESHOLD * 0.4;
                    currentVal = Math.abs(deltaYaw);
                } else if (direction === 'right') {
                    // nose.x decreases as user turns to their physical right (left side of camera image)
                    isTurned = deltaYaw < -AUDIO_YAW_THRESHOLD;
                    isReturned = Math.abs(deltaYaw) <= AUDIO_YAW_THRESHOLD * 0.4;
                    currentVal = Math.abs(deltaYaw);
                } else if (direction === 'up') {
                    isTurned = deltaPitch < -AUDIO_PITCH_THRESHOLD;
                    isReturned = Math.abs(deltaPitch) <= AUDIO_PITCH_THRESHOLD * 0.4;
                    currentVal = Math.abs(deltaPitch);
                } else if (direction === 'down') {
                    isTurned = deltaPitch > AUDIO_PITCH_THRESHOLD;
                    isReturned = Math.abs(deltaPitch) <= AUDIO_PITCH_THRESHOLD * 0.4;
                    currentVal = Math.abs(deltaPitch);
                }

                if (!turned) {
                    if (isTurned) {
                        turnHoldFrames++;
                        if (turnHoldFrames >= 10) {
                            turned = true;
                            peakValue = currentVal;
                            chime.next();
                            announce('Good turn detected! Now return to the centre.', 'Turn detected — Face forward');
                            speak('Good. Now face forward again.');
                        }
                    } else {
                        turnHoldFrames = 0; // reset if they drop out of threshold
                    }
                } else {
                    if (currentVal > peakValue) peakValue = currentVal;
                    if (isReturned) {
                        returnHoldFrames++;
                        if (returnHoldFrames >= 10) {
                            resolve({ ok: true, direction });
                            return;
                        }
                    } else {
                        returnHoldFrames = 0;
                    }
                }
            }

            if (performance.now() - t0 >= timeoutMs) {
                // If they turned but didn't return fully, we might accept it if it was a strong turn
                const threshold = (direction === 'left' || direction === 'right') ? AUDIO_YAW_THRESHOLD : AUDIO_PITCH_THRESHOLD;
                if (turned && peakValue >= threshold * 1.1) {
                    resolve({ ok: true, direction });
                    return;
                }
                resolve({ ok: false, direction });
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

function waitForCenter(timeoutMs) {
    return new Promise((resolve) => {
        const t0 = performance.now();
        const MAX_YAW = 0.05; // Strict straight look horizontally
        
        const tick = () => {
            const yaw = currentYaw();
            if (yaw != null && Math.abs(yaw) < MAX_YAW) {
                // To prevent capturing a blink or blur frame, require at least some stability or just resolve immediately
                resolve(true);
                return;
            }
            if (performance.now() - t0 >= timeoutMs) {
                resolve(false);
                return;
            }
            requestAnimationFrame(tick);
        };
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

    const allDirs = ['left', 'right', 'up', 'down'];
    // Randomly select 2 unique directions
    const dir1 = allDirs.splice(Math.floor(Math.random() * allDirs.length), 1)[0];
    const dir2 = allDirs.splice(Math.floor(Math.random() * allDirs.length), 1)[0];

    const checks = [
        { label: 'Face detected and tracked live', passed: false },
        { label: `Look ${dir1} and back to centre`, passed: false },
        { label: `Look ${dir2} and back to centre`, passed: false },
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
            speak('I could not find your face. The verification will now terminate.');
            chime.fail();
            await wait(2500);
            showResults('NOT_CONFIRMED', checks, 0);
            return;
        } else {
            chime.ok();
            announce('Please look straight forward at the camera.', 'Calibrating center position…');
            speak('Thank you. Please look straight at the camera to calibrate.');
            
            const centered = await waitForCenter(6000);
            if (!centered) {
                announce('Could not verify straight face.', 'Calibration Failed');
                speak('I could not verify you are looking straight. The verification will now terminate.');
                chime.fail();
                await wait(2000);
                showResults('NOT_CONFIRMED', checks, 0);
                return;
            } else {
                chime.ok();
                speak('Perfect.');
            }
            await wait(1200);
        }

        // Measure baseline
        const baselineYaw = await measureBaselineYaw(800);
        const baselinePitch = await measureBaselinePitch(800);

        // Turn 1
        renderAudioSteps(3, 0, 0);
        announce(`Slowly look ${dir1}, then back to the centre.`, `Waiting for a head movement ${dir1}`);
        speak(`Slowly look ${dir1}, then bring it back to the centre.`);
        const turn1 = await waitForSpecificTurn(dir1, baselineYaw, baselinePitch, AUDIO_TURN_TIMEOUT_MS);
        checks[1].passed = turn1.ok;
        
        if (turn1.ok) {
            chime.ok();
            renderAudioSteps(3, 1, 1);
            speak('Great.');
        } else {
            chime.fail();
            renderAudioSteps(3, 0, 1);
            announce('Failed to verify movement.', 'Verification Failed');
            speak('I did not detect the correct movement. The verification will now terminate.');
            await wait(2000);
            showResults('NOT_CONFIRMED', checks, 0);
            return;
        }
        await wait(1000);

        // Re-center
        announce('Please look straight forward again.', 'Centering…');
        speak('Please look straight forward again.');
        const centered2 = await waitForCenter(5000);
        if (!centered2) {
            announce('Could not verify straight face.', 'Verification Failed');
            speak('I could not verify you returned to the centre. The verification will now terminate.');
            chime.fail();
            await wait(2000);
            showResults('NOT_CONFIRMED', checks, 0);
            return;
        }
        const baselineYaw2 = await measureBaselineYaw(500);
        const baselinePitch2 = await measureBaselinePitch(500);

        // Turn 2
        announce(`Now slowly look ${dir2}, then back to the centre.`, `Waiting for a head movement ${dir2}`);
        speak(`Now slowly look ${dir2}, then back to the centre.`);
        const turn2 = await waitForSpecificTurn(dir2, baselineYaw2, baselinePitch2, AUDIO_TURN_TIMEOUT_MS);
        checks[2].passed = turn2.ok;
        
        if (turn2.ok) {
            chime.ok();
            renderAudioSteps(3, 2, 2);
            speak('Perfect.');
        } else {
            chime.fail();
            announce('Failed to verify movement.', 'Verification Failed');
            speak('I did not detect the correct movement. The verification will now terminate.');
            await wait(2000);
            showResults('NOT_CONFIRMED', checks, 0);
            return;
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
