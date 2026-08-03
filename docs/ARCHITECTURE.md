# Architecture Diagrams — Doctor eKYC Service

This document describes the **system context**, **runtime components**, **verification pipeline**, and **deployment** views of the Zudoc Doctor Portal eKYC service.

> Diagrams use [Mermaid](https://mermaid.js.org/). They render on GitHub and in most Markdown previewers.

---

## 1. System context

```mermaid
flowchart LR
  Doctor[Doctor]
  Admin[Admin Reviewer]
  Portal[MedTrust Web Portal<br/>public/]
  API[Doctor Verification Service<br/>Go HTTP API]
  PG[(PostgreSQL / SQLite)]
  OCR[OCR Provider<br/>Mock / Azure / Google]
  Council[Medical Council<br/>NMC Adapter]
  SMS[SMS Provider<br/>Mock / MSG91 / Twilio]
  Store[Object Storage<br/>Local / S3 / Cloudinary]
  MQ[[RabbitMQ / Event Bus]]
  Redis[(Redis)]

  Doctor --> Portal
  Admin --> Portal
  Portal --> API
  API --> PG
  API --> OCR
  API --> Council
  API --> SMS
  API --> Store
  API --> MQ
  API --> Redis
```

---

## 2. Runtime component view

```mermaid
flowchart TB
  subgraph Edge["Edge"]
    Nginx[Nginx Reverse Proxy]
  end

  subgraph App["doctor-service process"]
    Mux[HTTP ServeMux]
    RL[Rate Limiter]
    Controllers[Controllers]
    Services[Services]
    Worker[Verification Worker]
    Pipeline[Verification Pipeline]
    Repos[Repositories]
    Metrics[Health + Metrics]
  end

  subgraph Data["Data plane"]
    DB[(DB)]
    Uploads[File Storage]
  end

  subgraph Engines["Verification engines"]
    OCREng[OCR]
    Comp[Comparator]
    Coun[Council]
    Fraud[Fraud Detector]
    Dec[Decision Engine]
  end

  Nginx --> Mux
  Mux --> RL --> Controllers
  Controllers --> Services
  Services --> Repos --> DB
  Services --> Uploads
  Services -->|enqueue job| DB
  Worker -->|poll QUEUED| Repos
  Worker --> Pipeline
  Pipeline --> OCREng
  Pipeline --> Comp
  Pipeline --> Coun
  Pipeline --> Fraud
  Pipeline --> Dec
  Mux --> Metrics
```

---

## 3. Package / layered architecture

```mermaid
flowchart TB
  subgraph Presentation
    C[controllers]
    P[public UI]
    O[observability]
  end

  subgraph Application
    S[services]
    W[worker]
  end

  subgraph Domain
    E[entities]
    V[verification/*]
    A[auth/*]
    Sec[security]
    Rx[prescriptions]
  end

  subgraph Infrastructure
    R[repositories]
    St[storage]
    SMS[sms]
    OCR[ocr]
    Ev[events]
    N[notifications]
    Cfg[config]
  end

  P --> C
  C --> S
  C --> Sec
  S --> R
  S --> V
  S --> A
  S --> St
  S --> SMS
  S --> N
  W --> S
  V --> OCR
  R --> E
```

---

## 4. Doctor verification sequence

```mermaid
sequenceDiagram
  actor D as Doctor
  participant UI as Portal
  participant API as HTTP API
  participant S as SubmissionService
  participant DB as Database
  participant W as Worker
  participant PL as Pipeline
  actor AD as Admin

  D->>UI: Register / OTP / Login
  UI->>API: Auth endpoints
  API->>DB: Persist doctor + tokens

  D->>UI: Upload docs + profile data
  UI->>API: Documents / licenses / quals
  API->>DB: Store metadata + files

  D->>UI: Submit verification
  UI->>API: POST /submit-verification
  API->>S: Checklist validate
  S->>DB: Insert VerificationJob QUEUED

  loop Poll every ~2s
    W->>DB: FetchNextQueuedJob
    W->>PL: ProcessVerificationJob
    PL->>PL: OCR → Compare → Council → Fraud → Decision
    PL->>DB: OCR results + history + job status
  end

  AD->>UI: Open admin review
  UI->>API: Get verification detail
  AD->>API: Approve / Reject / Request docs
  API->>DB: Status + admin actions + notes
```

---

## 5. Verification pipeline detail

```mermaid
flowchart TD
  Start([Job QUEUED]) --> MarkRun[Mark RUNNING]
  MarkRun --> Load[Load doctor, docs, licenses, quals]
  Load --> OCR[OCR each document]
  OCR --> PersistOCR[Persist DocumentOCRResult]
  PersistOCR --> Compare[Compare OCR vs declared fields]
  Compare --> Council[Council registry lookup]
  Council --> Fraud[Fraud rule evaluation]
  Fraud --> Decide[Decision engine]
  Decide --> History[Write VerificationHistory]
  History --> Done{Success?}
  Done -->|yes| Complete[Mark COMPLETED]
  Done -->|no| Fail[Mark FAILED]
  Fail --> DLQ[Optional DLQ + admin retry]
```

---

## 6. Auth flow

```mermaid
sequenceDiagram
  participant C as Client
  participant API as AuthController
  participant AS as AuthService
  participant SMS as SMS Provider
  participant DB as DB

  C->>API: POST /register
  API->>AS: Create doctor + hash password
  AS->>DB: Save doctor
  AS->>SMS: Send OTP
  AS->>DB: Store OTPVerification

  C->>API: POST /verify-otp
  API->>AS: Validate OTP
  AS->>DB: Mark verified
  AS-->>C: Access JWT + Refresh token

  C->>API: POST /login
  API->>AS: Check credentials / lockout
  AS-->>C: Tokens
```

---

## 7. Deployment (Compose / K8s)

```mermaid
flowchart LR
  subgraph Compose["docker-compose"]
    NGX[nginx :80]
    APP[doctor-service :8080]
    PG[(postgres)]
    RD[(redis)]
    RMQ[rabbitmq]
    NGX --> APP
    APP --> PG
    APP --> RD
    APP --> RMQ
  end

  subgraph K8s["Kubernetes"]
    Ing[Ingress]
    Svc[Service]
    Dep[Deployment x3 + HPA]
    CM[ConfigMap]
    Sec[Secret]
    Ing --> Svc --> Dep
    Dep --> CM
    Dep --> Sec
  end
```

---

## 8. Trust boundary summary

| Boundary | Control |
|----------|---------|
| Public internet → API | Nginx, rate limits, JWT |
| Untrusted uploads → storage | Validator, scanner, size caps |
| Doctor → prescriptions | Verified-status guard |
| Pipeline → external council/OCR | Provider interfaces + timeouts/errors → job fail/DLQ |
| Admin actions → doctor status | Explicit admin APIs + action audit trail |
