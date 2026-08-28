# Design Document — Doctor eKYC Verification Service

## 1. Purpose

This service is the **doctor verification (eKYC) engine** for the Zudoc Doctor Portal. It lets licensed medical practitioners prove identity and credentials so the platform can trust them for clinical workflows (e.g. prescriptions).

Goals:

1. **Trust** — multi-signal verification (documents, OCR, council registry, fraud rules, human admin).
2. **Safety** — only verified doctors unlock sensitive actions.
3. **Operability** — async jobs, DLQ, health/metrics, container + K8s deployment.
4. **Developer velocity** — layered Python FastAPI architecture, provider interfaces, local OCR microservice.

---

## 2. High-level design

```
Doctor / Admin UI (public/)
        │
        ▼
   HTTP API (python_backend/main.py + controllers)
        │
   ┌────┴────┐
   │ Services│  ← auth, profile, documents, submission, admin review, analytics
   └────┬────┘
        │
   Repositories (SQLAlchemy) ──► PostgreSQL
        │
   On submit ──► VerificationJob (QUEUED)
        │
   OCR microservice (ocr_service/) ──► PaddleOCR / RetinaFace / face match
        │
   Verification Pipeline
              OCR → Compare → Council → Fraud → Decision
                              │
                         Admin review / Approve|Reject
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full diagrams.

---

## 3. Domain model (core entities)

| Entity | Role |
|--------|------|
| `Doctor` | Account, verification status, profile |
| `DoctorLicense` / `DoctorQualification` / `DoctorClinic` | Credential & practice data |
| `DoctorDocument` | Uploaded files + metadata/hash/version |
| `VerificationJob` | Async pipeline unit of work |
| `DocumentOCRResult` | Extracted fields from documents |
| `VerificationHistory` | Status transitions |
| `AdminUser` / `AdminAction` / `DoctorNote` / `VerificationFlag` | Human review trail |
| `AuditEvent` / `VerificationDeadJob` | Compliance & failure recovery |
| `OTPVerification` / `RefreshToken` | Auth lifecycle |
| `Prescription` | Post-verification clinical artifact |

Schema evolves via `migrations/*.sql` plus SQLAlchemy `Base.metadata.create_all` at startup for local/dev convenience.

---

## 4. Layered architecture

| Layer | Packages | Responsibility |
|-------|----------|----------------|
| Transport | `python_backend/controllers/`, `main.py` | HTTP routing, rate limits, guards |
| Application | `python_backend/services/` | Use-cases, orchestration, pipeline |
| Domain | `python_backend/entities/`, `verification/*`, `security/*` | Models, rules, engines |
| Infrastructure | `repositories/`, `storage/`, `sms/`, `ocr/`, `ocr_service/` | IO adapters + OCR microservice |

**Why this shape:** keeps business rules testable without HTTP/DB, and allows swapping providers (mock OCR ↔ Azure/Google, local storage ↔ S3/Cloudinary, mock SMS ↔ MSG91/Twilio).

---

## 5. Verification pipeline

Triggered when a doctor calls **submit verification** after checklist validation (profile, license, docs, etc.).

1. **Enqueue** — `VerificationJob` with type `FULL_PIPELINE` (or OCR-only).
2. **Worker** — polls queued jobs every ~2s (`worker/`).
3. **OCR** — provider extracts text/fields from uploaded documents.
4. **Comparison** — fuzzy/structured match of OCR vs doctor-entered data.
5. **Council** — NMC (or fallback) registry adapter validates registration numbers.
6. **Fraud** — rule-based detector surfaces anomalies.
7. **Decision engine** — combines signals into a recommended outcome / risk posture.
8. **Admin** — humans approve, reject, or request more documents; notes and flags are audited.

Failures mark the job failed; persistent failures can land in the **DLQ** for retry via admin APIs.

---

## 6. Auth & security design

| Concern | Approach |
|---------|----------|
| Registration | Password hashing + SMS OTP (`purpose=REGISTER`) |
| Session | Short-lived JWT access (~15m) + long-lived refresh tokens |
| Abuse | Per-route rate limiter; login attempt lockout via config |
| Uploads | Size/type validation, virus scanner hook, content hashing |
| Prescriptions | `PrescriptionAuthGuard` — requires verified doctor |
| Secrets | Env-driven (`JWT_SECRET`, DB creds); K8s Secret manifest |
| Encryption | Field/crypto helpers in `security/` for sensitive payloads |

RBAC hooks exist for admin vs doctor paths; admin review APIs are the human control plane.

---

## 7. Storage & files

`storage.StorageProvider` interface with:

- **Local** (default for demos) — `./uploads` served under `/uploads/`
- **S3** / **Cloudinary** — production-oriented adapters

Documents are never trusted as-is: validator + scanner run before persistence.

---

## 8. Events & messaging

- In-process **memory event bus** for local composition.
- Docker Compose wires **RabbitMQ** (+ Redis) for production-shaped topology.
- Design intent: publish verification lifecycle events for notifications and cross-service consumers without coupling the pipeline to a specific broker in core logic.

---

## 9. Observability & resilience

- `/health/live` — process up
- `/health/ready` — DB reachable
- `/metrics` — in-process metrics registry
- Graceful shutdown on SIGINT/SIGTERM (worker cancel + HTTP shutdown)
- HPA + probes in `k8s/` for horizontal scale

---

## 10. Frontend (portal)

`public/` ships a single-page **MedTrust** UI:

- **Doctor wizard** — multi-step registration → credentials → documents → submit
- **Admin portal** — queue/search, detail review, actions

The FastAPI server serves static assets from `/` so one process demos the full loop.

---

## 11. Deployment topology

| Mode | Notes |
|------|--------|
| Local Python | FastAPI + OCR service + PostgreSQL |
| Compose | App + OCR + Postgres + Redis + RabbitMQ + Nginx |
| Kubernetes | 3-replica Deployment, Ingress, ConfigMap/Secret, HPA |

CI (GitHub Actions): Python compile checks, Docker image build on `main`/`master`.

---

## 12. Extensibility guidelines

1. Add new verification signals as packages under `python_backend/verification/` and inject into the pipeline service.
2. Prefer new repository methods over leaking SQLAlchemy sessions into controllers.
3. Keep provider interfaces (OCR, SMS, storage, council, notifications) so mocks stay first-class in tests.
4. Evolve API contract in `docs/openapi.yaml` alongside handlers.
5. Prefer migration files for production schema changes; treat `create_all` as convenience, not the sole source of truth.

---

## 13. Non-goals (current scope)

- Full production SMS/OCR credentials baked into the repo
- Multi-tenant hospital org hierarchy
- Real-time WebSocket admin dashboards
- Replacing the medical council’s system of record

These can be layered on without changing the core pipeline boundaries above.
