# Computational Requirements — ZuDoc Doctor eKYC + Eye Tracking

This document estimates the **CPU, RAM, GPU, and storage** needed to run the full
ZuDoc eKYC experiment (portal API, document OCR, face extract/match, and live
eye / gaze tracking). Numbers are for a **single concurrent experimenter**
(one webcam, one browser session), not multi-tenant production scale.

---

## 1. What is loaded in one process

| Stage | Model / engine | Framework | Role |
|-------|----------------|-----------|------|
| OCR | PaddleOCR (EN det + rec) | PaddlePaddle | Read Aadhaar / PAN text |
| Face detect | RetinaFace | TensorFlow / Keras | Find faces on docs & live frames |
| Face match | ArcFace via DeepFace | TensorFlow | Compare 112×112 crops |
| ID region (optional) | YOLOv8n (`ultralytics`) | PyTorch | Document / card crop |
| Eye / pupil (primary) | MediaPipe Face Mesh + iris | MediaPipe | Live pupil (x,y) + facing gate |
| Gaze refine (optional) | FGI-Net (~1.52M params) | PyTorch | Pitch/yaw when trained weights exist |
| Backend | FastAPI + SQLAlchemy | Python | API, PostgreSQL, static UI |

**Dominant cost:** PaddleOCR + TensorFlow (RetinaFace + ArcFace) + MediaPipe in one
Python process. FGI-Net alone is light (~0.76 GFLOPs / forward; see §5).

---

## 2. Recommended hardware (lab / experiment)

### Minimum (CPU-only, slow but usable)

| Resource | Spec | Notes |
|----------|------|--------|
| **CPU** | 6–8 physical cores / 12–16 threads | e.g. Intel i5-10400 / Ryzen 5 3600 class |
| **Clock** | base ≥ 2.5 GHz, boost ≥ 4.0 GHz preferred | RetinaFace + OCR are latency-sensitive |
| **RAM** | **16 GB** system | Expect 8–12 GB used by the app peak |
| **GPU** | None required | All models can run on CPU |
| **VRAM** | — | — |
| **Storage** | 20 GB free SSD | Models + uploads + Postgres data |
| **Camera** | 720p webcam (30 FPS) | 1080p preferred for ID text |

**Expected feel:** Step 4.1 capture may take **5–20 s** per frame; eye graph ~10–20 FPS.

### Recommended (comfortable demo / research)

| Resource | Spec | Notes |
|----------|------|--------|
| **CPU** | 8–12 cores / 16–24 threads | e.g. Ryzen 7 5800H / Intel i7-11800H or better |
| **Clock** | base ≥ 3.0 GHz, boost ≥ 4.2 GHz | Helps TF + Paddle on CPU path |
| **RAM** | **32 GB** | Safe headroom for TF + Paddle + browser + Postgres |
| **GPU** | NVIDIA **GTX 1660 / RTX 3050** or better (6 GB+ VRAM) | Speeds YOLO / FGI / optional CUDA torch |
| **VRAM** | **6–8 GB** minimum if GPU used | TF RetinaFace often still CPU unless TF-GPU set up |
| **Storage** | 40 GB+ NVMe SSD | Faster model load & OCR I/O |
| **Camera** | 1080p @ 30 FPS | Better small printed-face detection |

**Expected feel:** OCR + face extract **2–8 s**; eye tracking **20–30+ FPS** with MediaPipe.

### Ideal (smooth full pipeline + GPU acceleration)

| Resource | Spec | Notes |
|----------|------|--------|
| **CPU** | 12+ cores / 20+ threads | Ryzen 9 / Intel i7/i9 HX or desktop equivalent |
| **Clock** | base ≥ 3.2 GHz, boost ≥ 4.5 GHz | |
| **RAM** | **32–64 GB** | Concurrent OCR + live cam + DB + tooling |
| **GPU** | NVIDIA **RTX 3060 / 4060** or better | **8–12 GB VRAM** |
| **CUDA** | CUDA 11.8+ / 12.x matching installed PyTorch | Optional TF-GPU for RetinaFace |
| **Storage** | 50 GB+ NVMe | |
| **OS** | Windows 10/11 64-bit or Ubuntu 22.04+ | Repo developed primarily on Windows |

---

## 3. Per-resource breakdown

### CPU

| Workload | Typical cores used | Why |
|----------|-------------------|-----|
| PaddleOCR | 2–4 | Det + rec on CPU/MKLDNN |
| RetinaFace (TF) | 2–6 | Heaviest per capture |
| ArcFace verify | 1–2 | Short burst |
| MediaPipe iris | 1–2 continuous | Live Step 4.2 loop |
| FGI-Net (CPU) | 1 | ~25 ms / forward (measured) |
| FastAPI + Postgres | 1–2 | Light |

**Rule of thumb:** plan for **≥ 8 logical cores** so OCR and live eye tracking do not starve each other.

### Clock speed

| Tier | Base clock | Boost clock |
|------|------------|-------------|
| Minimum | ≥ 2.5 GHz | ≥ 4.0 GHz |
| Recommended | ≥ 3.0 GHz | ≥ 4.2 GHz |
| Ideal | ≥ 3.2 GHz | ≥ 4.5 GHz |

Single-thread speed matters for TensorFlow RetinaFace and sequential OCR passes.

### RAM (system)

| Component (approx peak) | RAM |
|-------------------------|-----|
| Python process (Paddle + TF + MediaPipe + Torch) | 6–14 GB |
| Browser (portal + camera) | 1–3 GB |
| PostgreSQL | 0.5–2 GB |
| OS + misc | 2–4 GB |
| **Total recommended** | **16 GB min / 32 GB preferred** |

### GPU / VRAM

| Use | GPU needed? | VRAM estimate |
|-----|-------------|---------------|
| MediaPipe eye tracking | No (CPU/GPU delegate optional) | < 1 GB if GPU |
| FGI-Net 224×224 | Optional | < 1 GB |
| YOLOv8n | Optional | ~1–2 GB |
| PaddleOCR | Optional (Paddle-GPU build) | 1–3 GB |
| RetinaFace / ArcFace | Optional (TF-GPU) | 2–4 GB |
| **All GPU paths together** | Recommended RTX class | **6–8 GB+** |

**Important:** the current default path often runs **OCR + RetinaFace + ArcFace on CPU**, with PyTorch used for eye/YOLO when available. A GPU helps most if you install matching CUDA builds; otherwise RAM + strong CPU dominate.

---

## 4. Storage & network

| Item | Size (order of magnitude) |
|------|---------------------------|
| Repo + venv + wheels | 4–10 GB |
| PaddleOCR models (first download) | ~100–300 MB |
| RetinaFace / DeepFace weights | ~100–200 MB |
| YOLOv8n weights | ~6 MB |
| FGI-Net checkpoint | ~6 MB |
| Uploads / `ocr_uploads` during experiments | 1–5 GB+ |
| PostgreSQL data | hundreds of MB–GB |

Disk: **SSD strongly preferred**. HDD will make first-load and OCR feel much slower.

---

## 5. Measured FGI-Net footprint (repo benchmark)

From `python_backend/eye_tracking/weights/fgi_benchmark.json` (CPU run):

| Metric | Value |
|--------|-------|
| Parameters | ~1.52 M |
| Input | 1×3×224×224 |
| Approx FLOPs | ~0.76 GFLOPs / forward |
| Mean latency (CPU) | ~24.6 ms (~40 FPS alone) |
| State dict (FP32) | ~6 MB |

FGI-Net is **not** the compute bottleneck of the full eKYC stack; PaddleOCR + RetinaFace + ArcFace are.

---

## 6. Experiment profiles (what to provision)

| Experiment goal | Provision |
|-----------------|-----------|
| Portal + OCR only (no live cam) | 8-core CPU, 16 GB RAM, no GPU |
| Full Step 4.1 + 4.2 demo (this repo default) | 8–16 thread CPU, **32 GB RAM**, optional 6 GB GPU |
| Research: GPU-accelerated OCR + face + gaze | RTX 3060+, **32 GB RAM**, CUDA-matched PyTorch/TF |
| Multi-user / concurrent sessions | Scale **RAM and CPU linearly**; start 1 GPU per ~2–4 heavy sessions |

---

## 7. Software compute stack

| Package | Role |
|---------|------|
| `paddlepaddle` + `paddleocr` | OCR |
| `tensorflow` + `retinaface` + `deepface` | Face detect + ArcFace |
| `torch` ≥ 2.1 + `ultralytics` | YOLO / FGI-Net |
| `mediapipe==0.10.14` | Iris / pupil tracking |
| `opencv-contrib-python` | Preprocess, warp, quality |
| PostgreSQL | Persistence |

Python **3.10** is the validated lab path in-repo.

---

## 8. Summary cheat sheet

| | Minimum | Recommended | Ideal |
|-|---------|-------------|-------|
| **CPU** | 6c / 12t, ≥2.5 GHz | 8c / 16t, ≥3.0 GHz | 12c+, ≥3.2 GHz |
| **RAM** | 16 GB | **32 GB** | 32–64 GB |
| **GPU** | None | GTX 1660 / RTX 3050 (6 GB) | RTX 3060+ (8–12 GB) |
| **Storage** | 20 GB SSD | 40 GB NVMe | 50 GB+ NVMe |
| **Camera** | 720p | 1080p | 1080p 30 FPS |

**Bottom line:** to take this experiment end-to-end without fighting memory pressure, plan for **~32 GB RAM**, a **modern 8-core CPU (≥3 GHz)**, and treat a **6–8 GB NVIDIA GPU as optional acceleration**, not a hard requirement for the default CPU-centric install.
