# Verifyyy — Identity Verification OS, eKYC & Eye Tracking

Enterprise-style **doctor identity verification (eKYC)** for healthcare platforms, with **browser liveness** (WebGazer eye tracking or audio-guided checks for accessibility) and an optional standalone **FGI-Net** eye-tracking module.

**Repository:** [github.com/Saravanan2005real/zudoc-doctor-portal-EKYC](https://github.com/Saravanan2005real/zudoc-doctor-portal-EKYC)

## New Feature: B2B Pipeline Builder
The `customer_portal/` now includes a full B2B Pipeline Builder. Business clients can:
- Select from modules like **OCR**, **Liveness**, **Cross-Matching**, and **Fraud Analysis**.
- Generate an instant `verifyyy.com` integration link.
- Preview the generated end-user verification flow natively via `verify-session.html`.


---

## What this system does

| Goal | How it is achieved |
|------|--------------------|
| Trust doctors before clinical actions | Multi-step wizard + OCR of Aadhaar/PAN + face presence + name cross-match |
| Keep identity checks automated | **In-process OCR** (PaddleOCR + RetinaFace) inside the FastAPI app — no separate `:5001` process required |
| Prove a live person is present | Step 4.1 ID-hold capture + Step 4.2 dual-mode liveness (eye tracking **or** audio guided) |
| Persist audit trail | PostgreSQL via SQLAlchemy + verification history |
| Demo the full loop locally | One command: `python main.py` → portal + API + OCR on **:8080** |

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Portal UI | Vanilla HTML / CSS / JS (`python_backend/public/`) |
| Backend API | **FastAPI** + Uvicorn + Pydantic (`python_backend/`) |
| ORM / DB | SQLAlchemy 2 + **PostgreSQL** |
| OCR / faces | **In-process** PaddleOCR + RetinaFace + OpenCV (`python_backend/ocr/`) |
| Liveness (sighted) | **WebGazer.js** + MediaPipe Face Mesh (browser) |
| Liveness (accessible) | Speech synthesis + MediaPipe head-turn / blink checks |
| Auth | Password hash + SMS OTP (mock prints to console) + JWT / refresh tokens |
| Deploy | Docker Compose, Nginx, Kubernetes manifests |

> This repository is **Python-only**. The previous Go backend has been removed.

---

## System architecture (full platform)

One FastAPI process serves the **portal UI**, **REST API**, and **OCR / live-face** routes. Browser liveness (WebGazer or audio) runs client-side against the webcam.

```mermaid
flowchart TB
  subgraph Client["Browser + Webcam"]
    UI["Doctor Portal<br/>Steps 1–5 · public/"]
    WG["Step 4.2 Eye tracking<br/>WebGazer + Face Mesh"]
    AUD["Step 4.2 Audio guided<br/>speech + head / blink"]
    CAM["Webcam"]
  end

  subgraph Edge["Optional edge (Compose)"]
    NGX["Nginx :80"]
  end

  subgraph Backend["python_backend — single process :8080"]
    API["FastAPI / Uvicorn"]
    SVC["Services<br/>auth · documents · evaluate-ekyc · submit"]
    OCR["In-process OCR<br/>ocr/engine · ocr/inproc"]
    LIVE["Live face check<br/>POST /api/v1/live_face_check"]
    REPO["SQLAlchemy repositories"]
    STORE["uploads/ + ocr_uploads/"]
  end

  PG[("PostgreSQL")]

  UI -->|HTTP| NGX
  NGX --> API
  UI -->|local direct| API
  CAM --> UI
  UI --> WG
  UI --> AUD
  UI -->|"Step 4.1 frame"| LIVE
  API --> SVC
  SVC --> REPO --> PG
  SVC --> STORE
  SVC -->|"evaluate-ekyc"| OCR
  LIVE --> OCR
  API --> OCR
```

### Component map

| Component | Path | Port / entry | Responsibility |
|-----------|------|--------------|----------------|
| Portal + API + OCR | `python_backend/` | **:8080** (`python main.py`) | Auth, wizard, documents, **evaluate-ekyc**, live face, prescriptions, static UI |
| OCR engine | `python_backend/ocr/` | same process | Aadhaar/PAN OCR, RetinaFace crop, Verhoeff/format checks |
| Browser liveness | `python_backend/public/app.js` | browser | WebGazer eye tracking **or** audio-guided checks |
| Database | PostgreSQL | **:5433** local / **:5432** Compose | Doctors, docs, OTP, history |
| Nginx | `nginx.conf` | **:80** | Reverse proxy (Compose) |

See also: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`DESIGN.md`](DESIGN.md), [`computational.md`](computational.md).

---

## End-to-end doctor pipeline (Steps 1–5)

```mermaid
flowchart LR
  S1["Step 1<br/>Register / OTP / Login"] --> S2["Step 2<br/>License · Qualification · Clinic"]
  S2 --> S3["Step 3<br/>Upload documents<br/>+ Submit package"]
  S3 --> S41["Step 4.1<br/>Live ID hold"]
  S41 --> S42{"Step 4.2<br/>Choose mode"}
  S42 -->|Eye tracking| EYE["WebGazer + blink"]
  S42 -->|Audio guided| AUD["Head turns + blinks"]
  EYE --> EVAL["evaluate-ekyc<br/>OCR + decision"]
  AUD --> EVAL
  EVAL -->|AUTO_VERIFIED or MANUAL_REVIEW| S5["Step 5<br/>Prescription studio"]
  EVAL -->|FAILED| X["Blocked — fix docs / re-run"]
```

### Step 1 — Registration & auth

1. Register → `POST /api/v1/doctors/register`
2. Backend creates `Doctor` (`NOT_SUBMITTED`), hashes password, stores OTP
3. Mock SMS **prints OTP in the FastAPI terminal**
4. Verify → `POST /api/v1/doctors/verify-otp` → JWT + refresh token
5. Login → `POST /api/v1/doctors/login`

Wizard identity for later steps is primarily **`X-Doctor-Public-ID`**.

### Step 2 — Credentials

| Data | Endpoint |
|------|----------|
| License / council / year | `POST /api/v1/doctors/licenses` |
| Degree / university / year | `POST /api/v1/doctors/qualifications` |
| Clinic | `POST /api/v1/doctors/clinics` |
| Profile | `PUT /api/v1/doctors/profile` |

### Step 3 — Document vault + submit

1. Upload → `POST /api/v1/doctors/documents` (type + file + hash + versioning)
2. Checklist: mobile verified, license, qualification, clinic, reg cert, degree, govt ID
3. Submit → `POST /api/v1/doctors/submit-verification` → `PENDING`
4. UI advances to Step 4

### Step 4 — Live person check + eKYC evaluation

Step 4 has three phases:

| Phase | What happens |
|-------|----------------|
| **4.1 Live ID hold** | Webcam capture while holding Aadhaar/PAN; frame stored client-side; optional `POST /api/v1/live_face_check` (RetinaFace) |
| **4.2 Human verification** | User picks **Eye tracking** (WebGazer calibration + gaze targets + blink) **or** **Audio guided** (spoken prompts, head turns + blinks for blind / low-vision users) |
| **OCR evaluation** | `POST /api/v1/doctors/evaluate-ekyc` with **session document IDs** → in-process PaddleOCR + RetinaFace → decision |

```mermaid
flowchart TD
  A(["evaluate-ekyc"]) --> B[Load doctor]
  B --> C{OCR engine ready?}
  C -->|no| MR1[MANUAL_REVIEW]
  C -->|yes| D[Scope to session document_ids<br/>else latest vault KYC docs]
  D --> E["In-process OCR per doc<br/>PaddleOCR + RetinaFace"]
  E --> F{OCR success?}
  F -->|no| MR2[MANUAL_REVIEW / FAILED]
  F -->|yes| G[ID format + face presence]
  G --> H[Name similarity vs profile]
  H --> I{Decision}
  I -->|strong signals| AV[AUTO_VERIFIED]
  I -->|weak signals| MR3[MANUAL_REVIEW]
  I -->|no docs| FAIL[FAILED / REJECTED]
```

| Stage | Meaning |
|-------|---------|
| 1 Application Submitted | Package loaded |
| 2 OCR + Face Extraction | In-process OCR on scoped documents |
| 3 ID & Face Check | Verhoeff / PAN format + face crop present |
| 4 Name Cross-Match | OCR name vs profile (token + initial aware) |
| 5 Final Decision | `AUTO_VERIFIED` / `MANUAL_REVIEW` / `FAILED` |

**Decision summary**

- **AUTO_VERIFIED** — ID validated **or** (face + OCR conf ≥ 40%) **or** conf ≥ 60%
- **MANUAL_REVIEW** — OCR down / weak signals / soft mismatches
- **FAILED** — no documents (status → `REJECTED`)

UI also shows a **Live Person Verification** card (Step 4.1 frame + Step 4.2 pass/fail signals) above the OCR result cards.

### Step 5 — Prescription studio

Unlocked in UI when Step 4 is not `FAILED` → `POST /api/v1/prescriptions`.

---

## OCR pipeline (in-process on `:8080`)

OCR runs inside the FastAPI process via `ocr/inproc.py` (Flask test-client against `ocr/engine.py`). A standalone `:5001` process is optional only.

```mermaid
flowchart TD
  U([Upload / evaluate-ekyc]) --> Q[Quality check]
  Q --> W[Detect + perspective warp]
  W --> E["OCR-safe enhance<br/>mild CLAHE · SR only if soft/small"]
  E --> FACE[RetinaFace face crop<br/>TF_USE_LEGACY_KERAS=1]
  E --> PASS["Dual OCR pass<br/>mild vs raw → best parse"]
  PASS --> ROI["Aadhaar UID ROI refine<br/>bottom band digits"]
  ROI --> P[Parse Aadhaar / PAN]
  P --> R([JSON + face URL])
  FACE --> R
```

**Important OCR fixes in this tree**

- Aggressive Level-2 denoise/unsharp was harming Latin text → **mild enhance** by default
- Aadhaar Verhoeff no longer invents alternate digits to force VALID
- Prefers spaced `XXXX XXXX XXXX` and ROI OCR for the UID
- Rejects Tamil→Latin name garbage (e.g. `UDSIL IFTHIBLD`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/` | Demo UI + health |
| `GET` | `/live` | Live webcam verify UI |
| `POST` | `/api/v1/ocr` | Portal Step 4 OCR |
| `POST` | `/api/v1/live_verify` | Live frame + optional DeepFace |
| `GET` | `/ocr_uploads/<file>` | Crops / processed images |

---

## Eye tracking module (`python_backend/eye_tracking/`)

Standalone webcam module built around **FGI-Net** (*Fusion Global Information* gaze estimator) plus **MediaPipe Face Mesh** iris landmarks.

### Goals

1. Face may appear **anywhere** in the frame
2. Track + plot **only when both eyes face the camera**
3. Predict **top / bottom / left / right / center**
4. Live **(x, y)** graph for left and right pupils (`x,y ∈ [-1, 1]`)

### Architecture

```mermaid
flowchart TD
  CAM([Webcam frame]) --> MP[MediaPipe Face Mesh + iris]
  MP --> FACE{Both eyes open<br/>and facing camera?}
  FACE -->|no| WAIT[Pause plot<br/>turn_to_camera / no_face]
  FACE -->|yes| PUPIL[Per-eye pupil x,y]
  PUPIL --> CAL[Auto-center calibrator<br/>remove resting upward bias]
  CAL --> DIR[Direction classifier]
  CAL --> GRAPH[(x,y) graph L/R trails]
  DIR --> LABEL[Looking: TOP/BOTTOM/LEFT/RIGHT/CENTER]
  FACE -->|yes| FGI[FGI-Net face crop → pitch/yaw]
  FGI -.->|optional refine with real weights| DIR
```

### Package layout

```text
python_backend/eye_tracking/
├── FGI-Net/                 # Upstream architecture reference
├── fgi_eye_tracker/         # Our package
│   ├── fgi_net.py           # Import-safe FGI-Net
│   ├── face_eyes.py         # MediaPipe + OpenCV fallback
│   ├── eyes.py              # Pupil ROI + direction rules
│   ├── calibrate.py         # Resting-gaze center lock
│   ├── plot.py              # Live Cartesian graph
│   ├── tracker.py           # EyeTracker API
│   └── preprocess.py        # Face crop normalize for FGI-Net
├── weights/
│   ├── fgi_net.pth          # Checkpoint (architecture-init unless replaced)
│   └── fgi_benchmark.json   # Local size / latency numbers
├── demo.py
├── requirements.txt
└── scripts/
    ├── init_weights.py
    └── benchmark_fgi.py
```

### Run eye tracking

```powershell
cd python_backend/eye_tracking
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python demo.py
```

- Face the camera and look **straight** ~1s for auto-center calibration
- Then look top / bottom / left / right — graph updates while both eyes face the camera
- **Esc** to quit

### FGI-Net size & speed (measured on this project’s CPU host)

| Metric | Value |
|--------|------:|
| Parameters | **~1.52 M** |
| Checkpoint | **~6.1 MB** |
| Paper FLOPs / our MACs | **~0.38 G** |
| Mean latency (CPU, 224²) | **~25 ms** (~40 FPS) |
| Paper angular error (MPIIFaceGaze) | **3.74°** (needs author-trained weights) |

> Upstream [CZ178/FGI-Net](https://github.com/CZ178/FGI-Net) publishes architecture; trained paper weights are not on GitHub. Bundled `fgi_net.pth` is an architecture-compatible init for wiring/smoke tests unless you replace it. Direction in the demo is driven primarily by **iris geometry** (works without paper weights).

---

## Project structure

```text
eKYC/
├── python_backend/          # FastAPI portal (contains UI, OCR, and eye_tracking)
├── src/disability-app/      # Source code for the React Accessibility module
├── migrations/              # SQL migrations
├── docs/                    # ARCHITECTURE.md, openapi.yaml
├── k8s/                     # Kubernetes manifests
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
├── DESIGN.md
├── computational.md         # Hardware and compute requirements
└── README.md
```

---

## Prerequisites

- **Python 3.10+**
- **PostgreSQL** (`doctor_verification_db`) for the portal
- Webcam for eye tracking
- Optional: Docker / Docker Compose

---

## Quick start (portal + OCR)

### 1. Database

| Variable | Default |
|----------|---------|
| `DB_HOST` | `localhost` |
| `DB_PORT` | `5433` |
| `DB_USER` | `postgres` |
| `DB_PASSWORD` | `dinesh_2006` |
| `DB_NAME` | `doctor_verification_db` |

### 2. Portal (API + UI + OCR — one process)

```bash
cd python_backend
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

→ `http://127.0.0.1:8080` — OTP prints in the backend terminal. OCR and live-face routes run in the same process.

Optional: start a standalone OCR Flask process only if you need the legacy `:5001` UI (`OCR_STANDALONE=1 python -m ocr.engine`).

---

## Docker Compose

```bash
docker compose up --build
```

| Service | URL / port |
|---------|------------|
| Portal / API / OCR | http://localhost:8080 |
| Nginx | http://localhost:80 |
| Postgres | localhost:5432 |
| B2B Portal | http://localhost:8082 |
| Customer Portal (New) | http://localhost:8084 |

---

## Verifyyy Super Admin Dashboard

The platform includes a modern React-based Super Admin dashboard to manage companies, services, applications, and pipeline requests natively.

```bash
cd src/superadmin
npm install
npm run dev
```

→ `http://localhost:5173` — Super Admin Dashboard

---

## Key API surface

| Area | Endpoints |
|------|-----------|
| Auth | `POST /api/v1/doctors/register` · `/verify-otp` · `/login` |
| Credentials | `POST /api/v1/doctors/licenses` · `/qualifications` · `/clinics` |
| Documents | `POST/GET/DELETE /api/v1/doctors/documents` |
| Submit | `POST /api/v1/doctors/submit-verification` |
| **eKYC** | `POST /api/v1/doctors/evaluate-ekyc` |
| Live face | `POST /api/v1/live_face_check` · `/api/v1/live_verify` · `/api/v1/ocr` |
| Prescriptions | `POST /api/v1/prescriptions` |
| Health | `GET /health/live` · `/health/ready` · `/metrics` |

---

## Configuration

| Variable | Purpose |
|----------|---------|
| `JWT_SECRET` | Access token signing |
| `DB_*` | PostgreSQL |
| `PORT` | Backend listen port (default `8080`) |
| `TF_USE_LEGACY_KERAS` | Set to `1` for RetinaFace on TF 2.21 (set automatically in `main.py`) |

---

## Further reading

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Mermaid system / sequence / deploy views
- [`python_backend/eye_tracking/README.md`](python_backend/eye_tracking/README.md) — optional FGI-Net module
- [`DESIGN.md`](DESIGN.md) — design goals & extensibility
- [`computational.md`](computational.md) — hardware & compute requirements
- [`docs/openapi.yaml`](docs/openapi.yaml) — API contract

---

## License / status

Internal / project demo for ZuDoc doctor onboarding, eKYC evaluation, and gaze tracking experiments. Production SMS, cloud OCR credentials, author-trained FGI weights, and full admin review wiring remain provider swaps — see `DESIGN.md` non-goals.
