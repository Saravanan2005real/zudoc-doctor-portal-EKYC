# Zudoc Doctor Portal — eKYC / Doctor Verification Service

Enterprise-grade **doctor identity verification (eKYC)** backend and portal for the Zudoc ecosystem. Doctors register, upload licenses and credentials, and submit for automated + admin-assisted verification. Admins review side-by-side comparisons, OCR extracts, council checks, and fraud signals before approving or rejecting applications.

**Stack:** Go 1.22 · GORM · PostgreSQL (SQLite fallback) · JWT/OTP auth · background verification worker · Docker / Kubernetes

---

## Features

- **Doctor onboarding** — registration, OTP mobile verify, login with JWT access + refresh tokens
- **Profile & credentials** — licenses, qualifications, clinics, document uploads (validated + scanned)
- **Async verification pipeline** — OCR → field comparison → medical council lookup → fraud detection → decision engine
- **Admin review portal** — assign, approve, reject, request documents, notes, flags, analytics, DLQ retry
- **Prescription guard** — only verified doctors can create prescriptions
- **Ops ready** — health probes, metrics, rate limiting, Docker Compose, K8s manifests, CI workflow

---

## Quick start

### Prerequisites

- Go **1.22+**
- Optional: Docker & Docker Compose (Postgres, Redis, RabbitMQ, Nginx)

### Local (SQLite fallback)

If PostgreSQL is not running, the service automatically uses `./doctor_verification.db`.

```bash
go mod download
go run .
```

Open the portal: [http://localhost:8080/](http://localhost:8080/)  
API base: `http://localhost:8080/api/v1`

### Docker Compose

```bash
docker compose up --build
```

| Service    | Port        |
|------------|-------------|
| App (+ Nginx) | `80` → app `8080` |
| PostgreSQL | `5432`      |
| Redis      | `6379`      |
| RabbitMQ   | `5672` / UI `15672` |

### Tests

```bash
go test ./...
go vet ./...
```

---

## API overview

Full OpenAPI spec: [`docs/openapi.yaml`](docs/openapi.yaml)

| Area | Examples |
|------|----------|
| Auth | `POST /api/v1/doctors/register`, `/verify-otp`, `/login` |
| Profile | `/doctors/profile`, `/licenses`, `/qualifications`, `/clinics` |
| Documents | `POST /api/v1/doctors/documents` |
| Submit | `POST /api/v1/doctors/submit-verification` |
| Admin | `/admin/verifications/*`, `/admin/search`, `/admin/analytics` |
| DLQ | `/admin/dead-jobs`, `/admin/dead-jobs/retry` |
| Ops | `/health/live`, `/health/ready`, `/metrics` |

---

## Project layout

```
├── auth/              JWT, OTP, password, refresh tokens
├── controllers/       HTTP handlers
├── services/          Business logic & verification pipeline
├── repositories/      Data access (GORM)
├── entities/          Domain models
├── verification/      OCR comparison, council, fraud, decision
├── worker/            Background job poller
├── storage/           Local / S3 / Cloudinary providers
├── security/          Rate limit, RBAC, encryption, prescription guard
├── prescriptions/     Signed prescription generation
├── observability/     Health & metrics
├── migrations/        SQL schema versions
├── public/            MedTrust web portal (doctor wizard + admin)
├── k8s/               Kubernetes manifests
├── docs/              OpenAPI + architecture
├── DESIGN.md          System design decisions
└── main.go            Composition root & routes
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | HTTP listen port |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | localhost / 5432 / … | PostgreSQL connection |
| `JWT_SECRET` | (dev default) | Access-token signing key — **change in production** |
| `SMS_PROVIDER` | `MOCK` | `MOCK`, `MSG91`, or `TWILIO` |
| `REDIS_HOST` | — | Distributed locks / rate limit (Compose) |
| `RABBITMQ_URL` | — | Event bus (Compose) |

---

## Documentation

| Doc | Description |
|-----|-------------|
| [DESIGN.md](DESIGN.md) | Architecture rationale, flows, security, extensibility |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System & pipeline diagrams (Mermaid) |
| [docs/openapi.yaml](docs/openapi.yaml) | REST API contract |

---

## Deploy

**Kubernetes** (see `k8s/`): Deployment, Service, Ingress, ConfigMap, Secret, HPA.

```bash
kubectl apply -f k8s/
```

CI: `.github/workflows/ci-cd.yml` runs `go vet`, tests, and Docker build on `main`.

---

## License

Private — Zudoc / project owner. All rights reserved unless otherwise stated.
