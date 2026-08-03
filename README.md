# 🩺 ZuDoc — Enterprise Doctor Verification & eKYC Portal

> A production-grade, full-stack **Doctor Identity Verification System** built with **Go (Golang)** backend and a modern **HTML/CSS/JS** frontend. Designed for healthcare platforms to onboard, verify, and manage doctors through a secure, multi-step eKYC pipeline.

![Go Version](https://img.shields.io/badge/Go-1.26+-00ADD8?style=flat-square&logo=go)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=flat-square&logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation & Setup](#-installation--setup)
- [Running the Application](#-running-the-application)
- [API Reference](#-api-reference)
- [Doctor Verification Workflow](#-doctor-verification-workflow)
- [Security Features](#-security-features)
- [Admin Portal](#-admin-portal)
- [Configuration](#-configuration)
- [Contributing](#-contributing)

---

## 🔍 Overview

ZuDoc is an **enterprise-grade doctor verification and eKYC (Electronic Know Your Customer) platform** that automates the entire doctor onboarding lifecycle — from registration and OTP-based identity verification, through document upload and OCR-based validation, to NMC (National Medical Commission) registry cross-referencing and AI-powered fraud detection.

The system follows a **5-step wizard workflow** that guides doctors through:
1. **Account Registration & OTP Verification**
2. **Medical Credentials & Profile Setup**
3. **Secure Document Vault Upload**
4. **Automated Verification Pipeline**
5. **Digital Prescription Studio (RSA-256 Signed)**

---

## ✨ Key Features

### Doctor-Facing Features
- **Secure Registration & Login** — Password-hashed (bcrypt) accounts with account lockout protection
- **OTP-Based Mobile Verification** — 6-digit secure OTP with expiry and max-attempt limits
- **Split-Pane Auth UI** — Modern login/signup toggle interface with password visibility toggle
- **Medical License Management** — Save registration number, council, and year with dropdown for 40+ Indian Medical Councils
- **Qualification & Clinic Profiles** — Degree, specialization, hospital, and consultation fee management
- **Secure Document Vault** — Upload Medical Registration Certificate, Medical Degree Certificate, Post Graduate Certificate (optional), and KYC documents (Aadhaar/PAN/Passport)
- **SHA-256 File Hashing** — Every uploaded document is hashed for tamper-proof integrity
- **Virus Scanning** — All uploads pass through a virus scanner before being accepted
- **Real-Time Checklist** — Pre-submission verification checklist with dynamic green checkmarks
- **Delete Documents** — Remove individual documents with automatic checklist rollback
- **RSA-256 Digital Prescriptions** — Cryptographically signed, tamper-proof prescriptions with QR payloads

### Admin-Facing Features
- **Admin Analytics Dashboard** — Total doctors, pending reviews, auto-verification rate, dead letter queue metrics
- **Search & Filter** — Search doctors by name, mobile, or public ID
- **Side-by-Side Inspector** — Compare doctor-submitted claims against NMC registry data
- **Levenshtein Similarity Matching** — AI-based name matching with fraud scoring
- **Approve / Reject / Request Documents** — Full admin action workflow
- **Dead Letter Queue (DLQ)** — Failed verification jobs are captured and can be retried

### Infrastructure & Security
- **Public/Internal ID Architecture** — External APIs use UUID-based Public IDs; database uses internal IDs to prevent IDOR attacks
- **JWT + Refresh Token Authentication** — Short-lived access tokens with secure refresh rotation
- **Rate Limiting** — Request throttling to prevent brute-force and DDoS attacks
- **Account Lockout** — Automatic lockout after consecutive failed login attempts
- **Password Policy Enforcement** — Minimum complexity requirements for passwords
- **Background Worker Pool** — Async verification pipeline processing with retry logic
- **Event Bus** — In-memory event bus for decoupled service communication

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (HTML/CSS/JS)                │
│              Modern Emerald-Green Theme UI               │
│         5-Step Wizard + Admin Portal Dashboard           │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP REST API
┌──────────────────────▼──────────────────────────────────┐
│                   Go HTTP Server                         │
│              Rate Limiter ← Security Guard               │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │    Auth      │  │  Credential  │  │   Document     │  │
│  │  Controller  │  │  Controllers │  │   Controller   │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘  │
│         │                 │                  │           │
│  ┌──────▼─────────────────▼──────────────────▼────────┐  │
│  │              Service Layer (ID Translation)         │  │
│  │    PublicID → InternalID mapping via DoctorRepo     │  │
│  └──────┬─────────────────┬──────────────────┬────────┘  │
│         │                 │                  │           │
│  ┌──────▼─────────────────▼──────────────────▼────────┐  │
│  │            Repository Layer (GORM ORM)              │  │
│  └──────┬─────────────────────────────────────────────┘  │
│         │                                                │
│  ┌──────▼─────────────────────────────────────────────┐  │
│  │              PostgreSQL 15 Database                 │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │         Background Verification Worker              │  │
│  │   OCR → Council Registry → Fraud Engine → Decision  │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Go 1.26+, net/http (stdlib) |
| **Database** | PostgreSQL 15 |
| **ORM** | GORM v2 |
| **Authentication** | JWT (golang-jwt/v5), bcrypt, OTP |
| **Frontend** | HTML5, Vanilla CSS, Vanilla JavaScript |
| **Typography** | Google Fonts (Outfit, JetBrains Mono) |
| **Cryptography** | RSA-256 (Digital Signatures), SHA-256 (File Hashing), AES-GCM (Encryption) |
| **File Storage** | Local filesystem (pluggable to S3/GCS) |

---

## 📁 Project Structure

```
eKYC/
├── auth/                       # Authentication modules
│   ├── jwt/                    # JWT token generation & validation
│   ├── otp/                    # OTP generation, hashing & verification
│   ├── password/               # bcrypt password hashing & policy
│   └── token/                  # Refresh token management
├── config/                     # App configuration & feature flags
├── controllers/                # HTTP request handlers
│   ├── auth_controller.go      # Register, Login, Verify OTP
│   ├── document_controller.go  # Upload, List, Delete documents
│   ├── license_controller.go   # Medical license CRUD
│   ├── qualification_controller.go
│   ├── clinic_controller.go
│   ├── submission_controller.go
│   ├── admin_controller.go     # Admin review actions
│   ├── analytics_controller.go # Dashboard metrics
│   ├── prescription_controller.go
│   └── dlq_controller.go       # Dead Letter Queue management
├── dto/                        # Data Transfer Objects (request/response)
├── entities/                   # Database entity models (GORM)
├── events/                     # In-memory event bus
├── notifications/              # Notification providers (mock)
├── observability/              # Health checks & metrics
├── ocr/                        # OCR engine (mock provider)
├── prescriptions/              # RSA-256 digital prescription generator
├── public/                     # Frontend static files
│   ├── index.html              # Main SPA page (5-step wizard + admin)
│   ├── app.js                  # Frontend application logic
│   └── styles.css              # Emerald-green themed CSS
├── repositories/               # Database access layer (GORM repositories)
├── security/                   # Rate limiter, encryption, auth guards
├── services/                   # Business logic layer
│   ├── auth_service.go         # Registration, login, OTP flow
│   ├── license_service.go      # License CRUD with ID translation
│   ├── qualification_service.go
│   ├── clinic_service.go
│   ├── document_service.go     # Upload, hash, scan, store
│   ├── submission_service.go   # Pre-submission checklist validation
│   ├── verification_pipeline.go # Background OCR + council verification
│   ├── admin_review_service.go # Admin approve/reject/request docs
│   └── analytics_service.go   # Dashboard metrics aggregation
├── sms/                        # SMS providers (Mock + Twilio + MSG91)
├── storage/                    # File storage abstraction
│   ├── providers/local/        # Local filesystem storage
│   └── validator.go            # File type, size, resolution validation
├── verification/               # Verification engines
│   ├── comparison/             # Levenshtein string similarity
│   ├── council/                # NMC registry adapter
│   ├── decision/               # Auto-verify decision engine
│   └── fraud/                  # Fraud score calculator
├── worker/                     # Background job worker pool
├── main.go                     # Application entry point & DI wiring
├── go.mod                      # Go module definition
├── go.sum                      # Dependency checksums
├── Dockerfile                  # Container build configuration
└── docker-compose.yml          # Multi-service orchestration
```

---

## 📦 Prerequisites

Before running this project, ensure you have the following installed:

| Requirement | Version | Download |
|-------------|---------|----------|
| **Go** | 1.26 or higher | [golang.org/dl](https://golang.org/dl/) |
| **PostgreSQL** | 15+ | [postgresql.org](https://www.postgresql.org/download/) |
| **Git** | Latest | [git-scm.com](https://git-scm.com/) |

### Important: GOROOT Configuration

Make sure your `GOROOT` environment variable points to the Go installation directory (NOT the `bin` folder):

```
✅ Correct: GOROOT = C:\Program Files\Go
❌ Wrong:   GOROOT = C:\Program Files\Go\bin
```

To fix permanently on Windows:
```powershell
[System.Environment]::SetEnvironmentVariable('GOROOT', 'C:\Program Files\Go', [System.EnvironmentVariableTarget]::User)
```

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Saravanan2005real/zudoc-doctor-portal-EKYC.git
cd zudoc-doctor-portal-EKYC
```

### 2. Create the PostgreSQL Database

```sql
CREATE DATABASE doctor_verification_db;
```

Or via command line:
```bash
psql -U postgres -c "CREATE DATABASE doctor_verification_db;"
```

### 3. Install Go Dependencies

```bash
go mod tidy
```

### 4. Configure Database Connection

The database connection is configured in `main.go` with environment variable overrides:

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5433` | PostgreSQL port |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | *(set in code)* | Database password |
| `DB_NAME` | `doctor_verification_db` | Database name |
| `JWT_SECRET` | `super-secret-jwt-key-2026` | JWT signing secret |
| `PORT` | `8080` | HTTP server port |

You can override any of these via environment variables:
```powershell
$env:DB_PORT="5432"; $env:DB_PASSWORD="yourpassword"; go run .
```

---

## ▶️ Running the Application

### Start the Server

```powershell
# Windows (PowerShell)
$env:GOROOT="C:\Program Files\Go"; go run .

# Linux / macOS
go run .
```

### Expected Output

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

### Access the Application

Open your browser and navigate to: **http://localhost:8080/**

---

## 📡 API Reference

### Authentication APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/doctors/register` | Register a new doctor account |
| `POST` | `/api/v1/doctors/verify-otp` | Verify mobile OTP |
| `POST` | `/api/v1/doctors/login` | Login with email/mobile + password |

### Doctor Profile APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/PUT` | `/api/v1/doctors/profile` | Get or update doctor profile |
| `POST/GET` | `/api/v1/doctors/licenses` | Add or list medical licenses |
| `POST/GET` | `/api/v1/doctors/qualifications` | Add or list qualifications |
| `POST/GET` | `/api/v1/doctors/clinics` | Add or list clinic listings |

### Document Management APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/doctors/documents` | Upload a document (multipart) |
| `GET` | `/api/v1/doctors/documents` | List all uploaded documents |
| `DELETE` | `/api/v1/doctors/documents?document_id=UUID` | Delete a specific document |

### Verification APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/doctors/submit-verification` | Submit application for verification |
| `POST` | `/api/v1/prescriptions` | Generate RSA-256 signed prescription |

### Admin APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/admin/analytics` | Dashboard metrics |
| `GET` | `/api/v1/admin/search?q=query` | Search doctors |
| `GET` | `/api/v1/admin/verifications/detail?doctor_id=UUID` | Inspector detail |
| `POST` | `/api/v1/admin/verifications/approve` | Approve a doctor |
| `POST` | `/api/v1/admin/verifications/reject` | Reject a doctor |
| `POST` | `/api/v1/admin/verifications/request-documents` | Request better scans |

### Health & Observability

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health/live` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/metrics` | Application metrics |

> **Note:** All doctor-specific APIs require the `X-Doctor-Public-ID` header with the doctor's UUID.

---

## 🔄 Doctor Verification Workflow

### Step 1: Account & OTP Verification
- Doctor registers with name, mobile, email, and password
- A 6-digit OTP is sent to the registered mobile number
- OTP must be verified within the configured time window
- On successful OTP verification, JWT tokens are issued

### Step 2: Medical Credentials & Profile
- **Medical License**: Registration number, council (40+ Indian councils supported), and year
- **Qualifications**: Degree (MBBS/MD), specialization, college, and completion year
- **Clinic Practice**: Hospital name, city, and consultation fee

### Step 3: Document Vault Upload
Documents are categorized as:

| Document | Type | Required |
|----------|------|----------|
| Medical Registration Certificate | `REGISTRATION_CERTIFICATE` | ✅ Mandatory |
| Medical Degree Certificate | `MEDICAL_DEGREE_CERTIFICATE` | ✅ Mandatory |
| Post Graduate Certificate | `PG_CERTIFICATE` | ❌ Optional |
| Aadhaar Card | `AADHAAR` | ✅ Any one KYC |
| PAN Card | `PAN` | ✅ Any one KYC |
| Passport | `PASSPORT` | ✅ Any one KYC |

All uploads are:
- Virus-scanned before acceptance
- SHA-256 hashed for integrity verification
- Stored with version tracking

### Step 4: Automated Verification Pipeline
A background worker picks up the submitted application and runs:
1. **OCR Text Extraction** — Extracts registration numbers and names from document scans
2. **NMC Council Registry Verification** — Queries the official medical registry database
3. **AI Fraud & Levenshtein Analysis** — Cross-references document data with submitted claims
4. **Final Decision** — Auto-verify, flag for manual review, or reject

### Step 5: Digital Prescription Studio
Once verified, doctors can issue **RSA-256 digitally signed prescriptions** with:
- Unique prescription IDs
- Patient details and diagnosis
- Prescribed medication list
- Cryptographic digital signature
- QR code payload for verification

---

## 🔒 Security Features

| Feature | Implementation |
|---------|---------------|
| **Password Hashing** | bcrypt with salt |
| **JWT Tokens** | Short-lived (15 min) access + long-lived refresh tokens |
| **OTP Security** | SHA-256 hashed OTPs with expiry and max attempts |
| **ID Protection** | External Public UUID ↔ Internal Database ID translation |
| **Rate Limiting** | 60 requests/minute per endpoint |
| **Account Lockout** | Auto-lock after 5 failed login attempts |
| **File Validation** | Type, size (10MB max), and resolution checks |
| **Virus Scanning** | All uploads scanned before storage |
| **IDOR Prevention** | Service-layer PublicID → InternalID enforcement |

---

## 🛡️ Admin Portal

The admin portal provides a comprehensive dashboard for managing doctor verification:

- **Metrics Dashboard**: Total registered doctors, pending reviews, auto-verification rate, DLQ count
- **Search & Filter**: Find doctors by name, mobile number, or public ID
- **Verification Inspector**: Side-by-side comparison of doctor claims vs NMC registry data
- **Action Panel**: Approve, reject, or request additional documents
- **Dead Letter Queue**: View and retry failed verification jobs

---

## ⚙️ Configuration

### Feature Flags

The application supports feature flags defined in `config/feature_flags.go`:

- `EnableAdvancedOCR` — Toggle advanced OCR processing
- `EnableCouncilAPI` — Toggle live NMC council API calls
- `EnableFraudDetection` — Toggle AI fraud scoring
- `EnableNotifications` — Toggle SMS/email notifications

### Medical Councils Supported

The dropdown includes 40+ Indian Medical Councils:
Andhra Pradesh, Arunachal Pradesh, Assam, Bhopal, Bihar, Bombay, Chandigarh, Chhattisgarh, Delhi, Goa, Gujarat, Haryana, Himachal Pradesh, Hyderabad, Jammu & Kashmir, Jharkhand, Karnataka, Madhya Pradesh, Madras, Mahakoshal, Maharashtra, Manipur, Medical Council of Tanganyika, Meghalaya, Mizoram, Mysore, Nagaland, Orissa, Pondicherry, Punjab, Rajasthan, Sikkim, Tamil Nadu, Telangana, Travancore Cochin, Tripura, Uttar Pradesh, Uttarakhand, Vidarbha, West Bengal, and the National Medical Commission (NMC).

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

<p align="center">
  Built with ❤️ for the Indian Healthcare Ecosystem
</p>
