# Architecture — ZuDoc Doctor eKYC Portal + Eye Tracking

This document is the **source of truth** for system diagrams. It matches the **Python** runtime: FastAPI portal backend + Flask OCR microservice + PostgreSQL + FGI-Net eye-tracking module.

> Diagrams use [Mermaid](https://mermaid.js.org/) and render on GitHub.

For a shorter overview and setup guide, see the root [`README.md`](../README.md).

---

## 1. System context

```mermaid
flowchart LR
  Doctor[Doctor]
  Admin[Admin Reviewer]
  Portal[MedTrust Web Portal<br/>public/]
  API[FastAPI<br/>python_backend]
  PG[(PostgreSQL)]
  OCR[Flask OCR Microservice<br/>ocr_service :5001]
  Eye[Eye Tracking Module<br/>eye tracking/ FGI-Net]
  Cam[Webcam]
  SMS[SMS Provider<br/>Mock / MSG91 / Twilio]
  Store[Object Storage<br/>Local / S3 / Cloudinary]

  Doctor --> Portal
  Admin --> Portal
  Portal --> API
  API --> PG
  API -->|POST /api/v1/ocr| OCR
  API --> SMS
  API --> Store
  Cam --> Eye
```

**What is real today for the doctor wizard**

- Auth, credentials, documents, submit, **synchronous `evaluate-ekyc`**, UI Step 5
- OCR microservice for Aadhaar/PAN parse + RetinaFace face crop (OCR-safe enhance + UID ROI)

**Eye tracking (standalone demo today)**

- MediaPipe iris + both-eyes facing gate + (x,y) plot + direction classifier
- FGI-Net loaded for optional pitch/yaw refine when real weights are present

**Designed / partial**

- Async `VerificationJob` worker (council → fraud → decision)
- Full admin review service wiring (UI exists; many admin routes are stubs)
- Wiring eye-tracking signals into portal Step 4 / liveness
- Redis / RabbitMQ in Compose for a production-shaped topology

---

## 2. Runtime topology

```mermaid
flowchart TB
  subgraph Browser
    UI[public/ MedTrust UI]
  end

  subgraph ComposeEdge["Compose only"]
    NGX[Nginx :80]
  end

  subgraph FastAPI["python_backend"]
    HTTP[Uvicorn / FastAPI<br/>:8000 local · :8080 Docker]
    CTRL[Controllers]
    SVC[Services]
    REPO[Repositories]
    UP[uploads/]
  end

  subgraph FlaskOCR["ocr_service"]
    OHTTP[Flask :5001]
    OPIPE[Quality · Warp · SR · Face · OCR · Parse]
    OU[ocr_uploads/]
  end

  DB[(PostgreSQL)]

  UI --> NGX
  NGX --> HTTP
  UI -->|local direct| HTTP
  HTTP --> CTRL --> SVC
  SVC --> REPO --> DB
  SVC --> UP
  SVC --> OHTTP
  OHTTP --> OPIPE --> OU
```

| Process | Default local | Compose |
|---------|---------------|---------|
| Portal + API | `127.0.0.1:8000` | `:8080` (+ Nginx `:80`) |
| OCR | `127.0.0.1:5001` | `:5001` |
| Postgres | `:5433` (common local) | `:5432` |

Health:

- API: `GET /health/live`, `GET /health/ready`, `GET /metrics`
- OCR: `GET /` (also used as readiness probe by evaluate-ekyc)

---

## 3. Layered backend packages

```mermaid
flowchart TB
  subgraph Presentation
    P[public UI]
    C[controllers]
  end

  subgraph Application
    S[services]
    EKYC[ekyc_evaluation_service]
  end

  subgraph Domain
    E[entities]
    V[verification/*]
    SEC[security]
  end

  subgraph Infrastructure
    R[repositories]
    ST[storage]
    SMS[sms]
    HTTP_OCR[HTTP client → ocr_service]
  end

  P --> C
  C --> S
  C --> EKYC
  S --> R
  S --> ST
  S --> SMS
  EKYC --> HTTP_OCR
  EKYC --> R
  R --> E
  V -.->|designed async path| S
```

---

## 4. Doctor wizard sequence (live path)

```mermaid
sequenceDiagram
  actor D as Doctor
  participant UI as Portal public/
  participant API as FastAPI
  participant DB as PostgreSQL
  participant OCR as Flask OCR :5001

  D->>UI: Step 1 Register
  UI->>API: POST /api/v1/doctors/register
  API->>DB: Doctor + OTP hash
  API-->>UI: public_id (OTP printed in API logs)

  D->>UI: Enter OTP
  UI->>API: POST /api/v1/doctors/verify-otp
  API->>DB: mobile_verified + tokens
  API-->>UI: JWT + refresh

  D->>UI: Step 2 credentials
  UI->>API: POST licenses / qualifications / clinics
  API->>DB: Persist credential rows

  D->>UI: Step 3 upload docs
  UI->>API: POST /api/v1/doctors/documents
  API->>DB: DoctorDocument metadata
  API-->>UI: file_url under /uploads/...

  D->>UI: Submit verification
  UI->>API: POST /api/v1/doctors/submit-verification
  API->>DB: status PENDING + history (+ optional VerificationJob)

  UI->>API: POST /api/v1/doctors/evaluate-ekyc
  API->>OCR: GET / health
  loop Each KYC document
    API->>OCR: POST /api/v1/ocr multipart
    OCR-->>API: parsed_fields + face_image_url + confidence
  end
  API->>API: ID check · face presence · name score · decision
  API->>DB: status AUTO_VERIFIED / MANUAL_REVIEW / REJECTED
  API-->>UI: stages[] + decision + OCR cards

  alt not FAILED
    UI->>UI: Unlock Step 5 prescription studio
  else FAILED
    UI->>UI: Block — re-run / fix documents
  end
```

---

## 5. Step 4 evaluate-ekyc — decision pipeline

Entry: `POST /api/v1/doctors/evaluate-ekyc`  
Service: `python_backend/services/ekyc_evaluation_service.py`

```mermaid
flowchart TD
  Start([evaluate-ekyc]) --> Load[Load doctor by X-Doctor-Public-ID]
  Load --> Health{OCR GET / OK?}
  Health -->|no| MR_OCR[MANUAL_REVIEW<br/>OCR unreachable]
  Health -->|yes| Pick[Prefer AADHAAR/PAN/PASSPORT<br/>else first 2 docs]
  Pick --> Empty{Any docs?}
  Empty -->|no| FailEmpty[FAILED]
  Empty -->|yes| RunOCR[POST /api/v1/ocr per document]
  RunOCR --> AnyOK{≥1 success?}
  AnyOK -->|no| MR_or_Fail[MANUAL_REVIEW if errors<br/>else FAILED]
  AnyOK -->|yes| S3[Stage 3<br/>id_validated + face_detected + best_conf]
  S3 --> S4[Stage 4<br/>name Jaccard vs profile]
  S4 --> Rules{Decision}

  Rules -->|id_validated OR<br/>face && conf≥40 OR<br/>conf≥60| AV[AUTO_VERIFIED<br/>prescription_enabled=true<br/>fraud_score=0]
  Rules -->|weak / soft reasons| MR[MANUAL_REVIEW<br/>prescription_enabled=false<br/>fraud_score=30]
  Rules -->|hard empty path| RJ[REJECTED / FAILED<br/>fraud_score=80]

  AV --> Hist[VerificationHistory EKYC_EVALUATION]
  MR --> Hist
  RJ --> Hist
  MR_OCR --> Hist
  MR_or_Fail --> Hist
  FailEmpty --> Hist
```

### Soft reasons that push messaging toward MANUAL_REVIEW

- KYC present but ID number not validated
- KYC present but no face crop
- OCR name present and name similarity &lt; 40%

### UI vs backend unlock

| Decision | Backend `prescription_enabled` | Portal Step 5 button |
|----------|--------------------------------|----------------------|
| AUTO_VERIFIED | true | shown |
| MANUAL_REVIEW | false | shown (demo continuity) |
| FAILED | false | hidden |

---

## 6. OCR microservice internal pipeline

File: `ocr_service/app.py` — `POST /api/v1/ocr`

```mermaid
flowchart TD
  In([multipart image]) --> Save[Save to ocr_uploads/]
  Save --> Q[check_image_quality<br/>size · aspect · blur · brightness · Haar hints]
  Q --> Det[detect_and_warp_document<br/>YOLO optional + contour perspective]
  Det --> Enh[enhance_image_for_ocr<br/>FSRCNN_x2 · CLAHE · denoise · sharpen]
  Enh --> Face[extract_and_align_face<br/>RetinaFace → 112×112]
  Enh --> OCR[PaddleOCR → lines + avg confidence]
  OCR --> Parse[parse_id_document<br/>Aadhaar Verhoeff / PAN format]
  Parse --> Out([JSON status=success<br/>parsed_fields · face_image_url · processed_image_url])
  Face --> Out
```

### Optional live path (OCR demo UI only)

```mermaid
flowchart LR
  Cam[Webcam frame] --> Live["POST /api/v1/live_verify"]
  Live --> Same[Same OCR + face crop chain]
  Same --> DF[DeepFace verify vs step1 face]
  DF --> Res[face_match boolean + OCR fields]
```

Portal Step 4 does **not** call DeepFace. It only consumes `/api/v1/ocr`.

---

## 7. Document upload flow

```mermaid
sequenceDiagram
  participant UI as Portal
  participant API as DocumentController
  participant S as DocumentService
  participant V as Validator / Scanner
  participant FS as Local storage
  participant DB as DB

  UI->>API: POST /documents + X-Doctor-Public-ID
  API->>S: Upload
  S->>V: size / type / extension
  S->>V: SHA-256 hash + virus-scan hook
  S->>DB: reject duplicate hash for doctor
  S->>DB: version bump · previous not latest
  S->>FS: uploads/doctors/{public_id}/documents/{uuid}.ext
  S->>DB: DoctorDocument ocr_status=PENDING
  API-->>UI: document_id + file_url + file_hash
```

Supported types include: `REGISTRATION_CERTIFICATE`, medical degree variants, `AADHAAR`, `PAN`, `PASSPORT`.

---

## 8. Auth flow

```mermaid
sequenceDiagram
  participant C as Client
  participant API as AuthController
  participant AS as AuthService
  participant SMS as SMS Provider
  participant DB as DB

  C->>API: POST /register
  API->>AS: create doctor + hash password
  AS->>DB: save Doctor NOT_SUBMITTED
  AS->>SMS: send OTP (mock → console)
  AS->>DB: otp_verifications

  C->>API: POST /verify-otp
  API->>AS: validate OTP purpose=REGISTER
  AS->>DB: mobile_verified + refresh_token
  AS-->>C: access JWT + refresh + doctor

  C->>API: POST /login
  API->>AS: credentials + lockout checks
  AS-->>C: tokens + profile
```

---

## 9. Designed async job pipeline (secondary)

Submit may insert `VerificationJob` with status `QUEUED` and type `FULL_PIPELINE`.

```mermaid
flowchart TD
  Q([QUEUED]) --> Run[Mark RUNNING]
  Run --> Load[Load doctor + docs + licenses]
  Load --> OCR[OCR provider]
  OCR --> Comp[Compare OCR vs declared fields]
  Comp --> Council[Council / NMC adapter]
  Council --> Fraud[Fraud rules]
  Fraud --> Dec[Decision engine]
  Dec --> Hist[History + job COMPLETED]
  Dec -->|persistent failure| DLQ[verification_dead_jobs]
```

This path is **not** what Step 4 waits on. Day-to-day demos use synchronous `evaluate-ekyc`.

---

## 10. Deployment views

```mermaid
flowchart LR
  subgraph Compose["docker-compose"]
    NGX[nginx :80]
    APP[doctor-service :8080]
    OCR[ocr-service :5001]
    PG[(postgres :5432)]
    RD[(redis)]
    RMQ[rabbitmq]
    NGX --> APP
    APP --> PG
    APP --> OCR
    APP --> RD
    APP --> RMQ
  end

  subgraph K8s["Kubernetes k8s/"]
    Ing[Ingress]
    Svc[Service]
    Dep[Deployment ×3 + HPA]
    CM[ConfigMap]
    Sec[Secret]
    Ing --> Svc --> Dep
    Dep --> CM
    Dep --> Sec
  end
```

---

## 11. Trust boundaries

| Boundary | Control |
|----------|---------|
| Browser → API | Optional Nginx; route rate limits; JWT on auth paths |
| Uploads → disk | Type/size validation, content hash, scanner hook |
| API → OCR | HTTP timeouts (evaluate uses long OCR timeout); health check first |
| Doctor → prescriptions | `prescription_enabled` / verified-status intent (`PrescriptionAuthGuard`) |
| Admin → status changes | Explicit admin APIs + action audit (when fully wired) |
| Webcam → eye tracker | Local process only; both-eyes facing gate before plotting |

---

## 12. Eye tracking module (FGI-Net)

Standalone package under `eye tracking/`. Not yet wired into portal Step 4; intended as a liveness / attention signal.

```mermaid
flowchart TD
  Frame([Webcam BGR frame]) --> MP[MediaPipe Face Mesh + iris]
  MP --> Gate{Both eyes open<br/>and facing camera?}
  Gate -->|no| Wait[direction = turn_to_camera / no_face<br/>graph paused]
  Gate -->|yes| Raw[Raw pupil x,y per eye]
  Raw --> Cal[CenterCalibrator<br/>subtract resting bias]
  Cal --> Dir[classify_direction<br/>top/bottom/left/right/center]
  Cal --> Plot[EyeXYGraph trails]
  Gate -->|yes| Crop[Face crop 224×224]
  Crop --> FGI[FGI-Net → pitch,yaw]
  FGI -.->|optional with real weights| Dir
```

| Piece | Role |
|-------|------|
| `FaceEyeEngine` | Detect face anywhere; require both eyes facing |
| `CenterCalibrator` | Auto-lock resting gaze so plot center ≈ (0,0) |
| `EyeXYGraph` | Live Cartesian plot for left/right pupils |
| `FGI_Net` | Lightweight appearance gaze head (~1.5M params) |
| `demo.py` | Side-by-side camera + graph UI |

Run: `cd "eye tracking" && .\.venv\Scripts\activate && python demo.py`

---

## 13. Related files

| Concern | Path |
|---------|------|
| API entry | `python_backend/main.py` |
| Step 4 evaluate | `python_backend/services/ekyc_evaluation_service.py` |
| Evaluate route | `python_backend/controllers/evaluation_controller.py` |
| OCR service | `ocr_service/app.py` |
| Portal wizard | `public/app.js` |
| Eye tracker | `eye tracking/fgi_eye_tracker/tracker.py` |
| Eye demo | `eye tracking/demo.py` |
| Schema | `migrations/*.sql` |
| OpenAPI | `docs/openapi.yaml` |
