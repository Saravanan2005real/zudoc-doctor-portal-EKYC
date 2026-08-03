# ZuDoc — Enterprise Doctor Verification & eKYC Portal

> Production-grade **Doctor Identity Verification (eKYC)** for healthcare platforms. Built with a **Go** HTTP API and a modern **HTML/CSS/JS** portal so teams can onboard, verify, and manage doctors through a secure multi-step pipeline — from OTP registration to NMC-aligned review and RSA-signed prescriptions.

[![Go Version](https://img.shields.io/badge/Go-1.22+-00ADD8?style=flat-square&logo=go)](https://go.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=flat-square&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker)](https://docs.docker.com/compose/)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?style=flat-square&logo=githubactions)](.github/workflows/ci-cd.yml)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](#-license)

**Repository:** [github.com/Saravanan2005real/zudoc-doctor-portal-EKYC](https://github.com/Saravanan2005real/zudoc-doctor-portal-EKYC)

---

## Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Installation & Local Setup](#-installation--local-setup)
- [Running the Application](#-running-the-application)
- [Docker Compose](#-docker-compose)
- [Kubernetes](#-kubernetes)
- [API Reference](#-api-reference)
- [Doctor Verification Workflow](#-doctor-verification-workflow)
- [Security Features](#-security-features)
- [Admin Portal](#-admin-portal)
- [Configuration](#-configuration)
- [Documentation](#-documentation)
- [CI/CD](#-cicd)
- [Contributing](#-contributing)
- [License](#-license)

---

## Overview

ZuDoc is an **enterprise doctor verification and eKYC platform** that automates the doctor onboarding lifecycle:

1. **Account registration** with password hashing and OTP mobile verification  
2. **Medical credentials** — license, qualifications, clinic profile  
3. **Secure document vault** — registration certificate, degree, optional PG cert, KYC (Aadhaar/PAN/Passport)  
4. **Automated verification pipeline** — OCR → council registry → fraud scoring → decision  
5. **Admin review** — approve / reject / request documents, with DLQ retry  
6. **Digital prescription studio** — RSA-256 signed, tamper-evident prescriptions (verified doctors only)

The portal serves a **5-step wizard** for doctors and a full **admin analytics + inspector** console from the same Go process.

---

## Key Features

### Doctor-facing

| Feature | Detail |
|---------|--------|
| Secure registration & login | bcrypt passwords, account lockout after failed attempts |
| OTP mobile verification | 6-digit OTP with expiry and max-attempt limits |
| Split-pane auth UI | Login / Sign Up toggle, password visibility controls |
| Medical license management | Registration number, year, **40+ Indian Medical Councils** |
| Qualifications & clinics | Degree, specialization, hospital, consultation fee |
| Document vault | Registration cert, Medical Degree, optional PG cert, KYC proof |
| Integrity & safety | SHA-256 file hashing, virus-scan hook, type/size validation |
| Live checklist | Pre-submission checklist with dynamic completion state |
| Document delete | Remove uploads with checklist rollback |
| RSA-256 prescriptions | Cryptographically signed prescriptions + QR payload |

### Admin-facing

- Analytics dashboard (totals, pending reviews, auto-verify rate, DLQ depth)
- Search by name, mobile, or public UUID
- Side-by-side inspector (claims vs NMC/council data)
- Levenshtein similarity matching and fraud scoring
- Approve / Reject / Request documents
- Dead Letter Queue view and retry

### Infrastructure & security

- **Public UUID ↔ internal ID** translation (IDOR hardening)
- JWT access + refresh token rotation
- Per-route rate limiting
- Background worker pool for async verification
- In-memory event bus (RabbitMQ-ready via Compose)
- Health probes + metrics endpoints
- Docker Compose + Kubernetes manifests

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (HTML/CSS/JS)                │
│              Emerald-green light-theme UI                │
│         5-Step Wizard + Admin Portal Dashboard           │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP REST API
┌──────────────────────▼──────────────────────────────────┐
│                   Go HTTP Server                         │
│              Rate Limiter ← Security Guard               │
│                                                          │
│  Controllers → Services (PublicID → InternalID)          │
│                     ↓                                    │
│              Repositories (GORM)                         │
│                     ↓                                    │
│              PostgreSQL 15                               │
│                                                          │
│  Background Worker: OCR → Council → Fraud → Decision     │
└──────────────────────────────────────────────────────────┘
```

For Mermaid diagrams (system context, sequences, pipeline, deployment), see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).  
For design rationale and domain model, see [`DESIGN.md`](DESIGN.md).

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Go **1.22+**, `net/http` |
| Database | **PostgreSQL 15** (required — no SQLite fallback) |
| ORM | GORM v2 |
| Auth | JWT (`golang-jwt/v5`), bcrypt, OTP |
| Frontend | HTML5, CSS, Vanilla JavaScript |
| Typography | Outfit, JetBrains Mono |
| Crypto | RSA-256 (prescriptions), SHA-256 (files), AES-GCM helpers |
| Storage | Local FS (pluggable S3 / Cloudinary) |
| Messaging | In-process event bus; RabbitMQ + Redis in Compose |
| Deploy | Docker, Docker Compose, Kubernetes, Nginx |

---

## Project Structure

```
zudoc-doctor-portal-EKYC/
├── auth/                 # JWT, OTP, password, refresh tokens
├── config/               # App config & feature flags
├── controllers/          # HTTP handlers (auth, docs, admin, …)
├── dto/                  # Request/response DTOs
├── entities/             # GORM models
├── events/               # Event bus (+ RabbitMQ helper)
├── notifications/        # Notification providers (mock)
├── observability/        # Health & metrics
├── ocr/                  # OCR providers (mock / Azure / Google)
├── prescriptions/        # RSA-256 prescription generator
├── public/               # SPA: index.html, app.js, styles.css
├── repositories/         # Data access
├── security/             # Rate limit, encryption, RBAC, guards
├── services/             # Business logic & verification pipeline
├── sms/                  # Mock / Twilio / MSG91
├── storage/              # Storage abstraction + validators
├── verification/         # Comparison, council, fraud, decision
├── worker/               # Background job worker
├── migrations/           # SQL schema migrations
├── docs/                 # Architecture + OpenAPI
├── k8s/                  # Deployment, Service, Ingress, HPA, …
├── .github/workflows/    # CI/CD
├── main.go               # Entry point & DI wiring
├── Dockerfile
├── docker-compose.yml
├── DESIGN.md
└── README.md
```

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|--------|
| Go | 1.22+ | [golang.org/dl](https://golang.org/dl/) |
| PostgreSQL | 15+ | Required at runtime |
| Git | Latest | |
| Docker (optional) | Latest | For Compose / image builds |
| kubectl (optional) | Latest | For Kubernetes deploy |

### Windows: GOROOT

`GOROOT` must point at the Go **install root**, not `bin`:

```
Correct: C:\Program Files\Go
Wrong:   C:\Program Files\Go\bin
```

```powershell
[System.Environment]::SetEnvironmentVariable('GOROOT', 'C:\Program Files\Go', [System.EnvironmentVariableTarget]::User)
```

---

## Quick Start

```bash
git clone https://github.com/Saravanan2005real/zudoc-doctor-portal-EKYC.git
cd zudoc-doctor-portal-EKYC
```

**Option A — Docker Compose (recommended for first run)**

```bash
docker compose up --build
```

Open **http://localhost** (Nginx) or **http://localhost:8080** (app directly).

**Option B — Local Go + PostgreSQL**

```bash
# Create DB
psql -U postgres -c "CREATE DATABASE doctor_verification_db;"

go mod tidy
# Set DB_* env vars to match your Postgres, then:
go run .
```

Open **http://localhost:8080/**

---

## Installation & Local Setup

### 1. Clone

```bash
git clone https://github.com/Saravanan2005real/zudoc-doctor-portal-EKYC.git
cd zudoc-doctor-portal-EKYC
```

### 2. Create PostgreSQL database

```sql
CREATE DATABASE doctor_verification_db;
```

### 3. Install dependencies

```bash
go mod tidy
```

### 4. Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5433` | PostgreSQL port |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | *(from env / local config)* | Database password |
| `DB_NAME` | `doctor_verification_db` | Database name |
| `JWT_SECRET` | *(change in production)* | JWT signing secret |
| `PORT` | `8080` | HTTP listen port |
| `SMS_PROVIDER` | `MOCK` | `MOCK` / `TWILIO` / `MSG91` |

Example (PowerShell):

```powershell
$env:DB_PORT="5432"
$env:DB_PASSWORD="yourpassword"
$env:JWT_SECRET="replace-me-in-production"
go run .
```

> **Security:** Never commit real secrets. Prefer environment variables or Kubernetes Secrets. Rotate `JWT_SECRET` and DB credentials before any shared/staging deploy.

---

## Running the Application

```powershell
# Windows
$env:GOROOT="C:\Program Files\Go"; go run .

# Linux / macOS
go run .
```

Expected log excerpt:

```
=======================================================
Starting Enterprise Doctor Verification Service v1.0.0
=======================================================
[DB] Successfully connected to PostgreSQL database.
[DB] Running schema auto-migrations...
[DB] Schema auto-migrations completed successfully.
[BACKGROUND WORKER] Verification Worker started listening for QUEUED jobs...
Server listening and serving HTTP on port 8080...
Ready to receive requests at http://localhost:8080/
```

If PostgreSQL is unreachable, the process **exits fatally** with a clear error (no silent fallback).

### Tests

```bash
go vet ./...
go test ./...
```

---

## Docker Compose

`docker-compose.yml` brings up:

| Service | Port(s) | Role |
|---------|---------|------|
| `doctor-service` | `8080` | API + portal |
| `postgres` | `5432` | Primary DB |
| `redis` | `6379` | Cache / lock helper |
| `rabbitmq` | `5672`, `15672` | Messaging (+ management UI) |
| `nginx` | `80` | Reverse proxy |

```bash
docker compose up --build
docker compose down
```

Compose sets `DB_HOST=postgres`, `DB_PORT=5432`, and related secrets via environment blocks. Override secrets for any non-local environment.

---

## Kubernetes

Manifests live under [`k8s/`](k8s/):

| File | Purpose |
|------|---------|
| `deployment.yaml` | App Deployment |
| `service.yaml` | ClusterIP / Service |
| `ingress.yaml` | Ingress rules |
| `configmap.yaml` | Non-secret config |
| `secret.yaml` | Secrets template |
| `hpa.yaml` | Horizontal Pod Autoscaler |

Apply (after editing secrets/config for your cluster):

```bash
kubectl apply -f k8s/
```

Probes: `/health/live`, `/health/ready`. Metrics: `/metrics`.

---

## API Reference

> Doctor-scoped routes expect the doctor’s public UUID (see portal / auth flow). Prefer JWT where wired by the security layer.

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/doctors/register` | Register doctor |
| `POST` | `/api/v1/doctors/verify-otp` | Verify mobile OTP |
| `POST` | `/api/v1/doctors/login` | Login |

### Profile & credentials

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` / `PUT` | `/api/v1/doctors/profile` | Profile |
| `POST` / `GET` | `/api/v1/doctors/licenses` | Medical licenses |
| `POST` / `GET` | `/api/v1/doctors/qualifications` | Qualifications |
| `POST` / `GET` | `/api/v1/doctors/clinics` | Clinics |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/doctors/documents` | Upload (multipart) |
| `GET` | `/api/v1/doctors/documents` | List |
| `DELETE` | `/api/v1/doctors/documents?document_id=UUID` | Delete |

### Verification & prescriptions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/doctors/submit-verification` | Submit for pipeline |
| `POST` | `/api/v1/prescriptions` | RSA-256 signed prescription |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/admin/analytics` | Dashboard metrics |
| `GET` | `/api/v1/admin/search?q=` | Search doctors |
| `GET` | `/api/v1/admin/verifications/detail?doctor_id=` | Inspector |
| `POST` | `/api/v1/admin/verifications/approve` | Approve |
| `POST` | `/api/v1/admin/verifications/reject` | Reject |
| `POST` | `/api/v1/admin/verifications/request-documents` | Request docs |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health/live` | Liveness |
| `GET` | `/health/ready` | Readiness (DB) |
| `GET` | `/metrics` | Metrics |

Full machine-readable contract: [`docs/openapi.yaml`](docs/openapi.yaml).

---

## Doctor Verification Workflow

### Step 1 — Account & OTP

Register → OTP to mobile → verify → tokens issued.

### Step 2 — Medical credentials

- License: number, council, year  
- Qualifications: degree, specialization, college, year  
- Clinic: hospital, city, consultation fee  

### Step 3 — Document vault

| Document | Type constant | Required |
|----------|---------------|----------|
| Medical Registration Certificate | `REGISTRATION_CERTIFICATE` | Yes |
| Medical Degree Certificate | `MEDICAL_DEGREE_CERTIFICATE` | Yes |
| Post Graduate Certificate | `PG_CERTIFICATE` | Optional |
| Aadhaar / PAN / Passport | `AADHAAR` / `PAN` / `PASSPORT` | Any one KYC |

Uploads are validated, virus-scanned (hook), SHA-256 hashed, and versioned.

### Step 4 — Automated pipeline

Background worker:

1. OCR text/field extraction  
2. Council / NMC registry lookup  
3. Fraud + Levenshtein similarity analysis  
4. Decision → auto-verify, manual review, or reject  

### Step 5 — Prescription studio

Verified doctors can issue RSA-256 signed prescriptions with unique IDs, meds list, signature, and QR verification payload.

---

## Security Features

| Control | Implementation |
|---------|----------------|
| Passwords | bcrypt |
| Sessions | Short-lived JWT + refresh rotation |
| OTP | Hashed OTP, expiry, attempt caps |
| IDOR defense | Public UUID → internal ID in services |
| Abuse | Rate limits; login lockout |
| Uploads | Type/size/resolution checks + scanner hook |
| Prescriptions | Verified-doctor guard |
| Secrets | Env / K8s Secret (do not hardcode in prod) |

---

## Admin Portal

- Metrics: registered doctors, pending queue, auto-verify rate, DLQ  
- Search & filter  
- Side-by-side claim vs registry inspector  
- Approve / reject / request documents with notes  
- DLQ retry for failed jobs  

---

## Configuration

### Feature flags (`config/`)

Typical toggles include advanced OCR, live council API, fraud detection, and notifications. Prefer flags for gradual rollout of external providers.

### Medical councils

UI dropdown covers **40+** Indian state/historical councils plus **NMC**, including Andhra Pradesh, Assam, Bihar, Delhi, Gujarat, Karnataka, Maharashtra, Tamil Nadu, Telangana, West Bengal, and others listed in the portal.

---

## Documentation

| Doc | Contents |
|-----|----------|
| [`DESIGN.md`](DESIGN.md) | Goals, domain model, pipeline, security design |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Mermaid system / sequence / deploy diagrams |
| [`docs/openapi.yaml`](docs/openapi.yaml) | OpenAPI contract |

---

## CI/CD

GitHub Actions (`.github/workflows/ci-cd.yml`) on `main` / PRs:

1. `go mod verify`  
2. `go vet ./...`  
3. `go test` (race + coverage)  
4. Docker image build on `main`  

---

## Contributing

1. Fork the repository  
2. Create a feature branch: `git checkout -b feature/your-feature`  
3. Commit with a clear message  
4. Push and open a Pull Request  

Guidelines:

- Keep business logic in `services/`; avoid leaking GORM into controllers  
- Extend verification via packages under `verification/`  
- Update `docs/openapi.yaml` when changing HTTP contracts  
- Prefer SQL migrations for production schema changes  

---

## License

This project is licensed under the **MIT License**.

---

<p align="center">
  Built for the Indian healthcare ecosystem — ZuDoc Doctor Portal eKYC
</p>
