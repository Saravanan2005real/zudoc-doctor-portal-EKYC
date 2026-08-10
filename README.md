# ZuDoc — Enterprise Doctor Verification & eKYC Portal (Python)

Production-grade **Doctor Identity Verification (eKYC)** for healthcare platforms. The stack is fully **Python**:

- **FastAPI** doctor portal backend (`python_backend/`)
- **Flask OCR + Face Matching microservice** (`ocr_service/`)
- **PostgreSQL** for persistence
- **HTML/CSS/JS** portal (`public/`)

**Repository:** [github.com/Saravanan2005real/zudoc-doctor-portal-EKYC](https://github.com/Saravanan2005real/zudoc-doctor-portal-EKYC)

---

## Architecture

```
Browser (public/)
      │
      ▼
FastAPI backend :8080 / :8000   ←── PostgreSQL
      │
      ▼
OCR microservice :5001
  (PaddleOCR + RetinaFace + OpenCV SR/CLAHE)
```

See also: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [DESIGN.md](DESIGN.md)

---

## Project Structure

```
eKYC/
├── python_backend/     # FastAPI API, SQLAlchemy, services, frontend copy
├── ocr_service/        # Aadhaar/PAN OCR + face extract/match (Flask)
│   ├── app.py
│   ├── FSRCNN_x2.pb    # Super-resolution model
│   └── requirements.txt
├── public/             # Portal UI (index.html, app.js, styles.css)
├── migrations/         # SQL migrations
├── docs/               # Architecture docs
├── docker-compose.yml
└── Dockerfile
```

---

## Prerequisites

- Python 3.10+
- PostgreSQL (local default: `localhost:5433`)
- Optional: Docker / Docker Compose

---

## Quick Start (Local)

### 1. Database

Ensure PostgreSQL is running with database `doctor_verification_db`.

Default env used by the backend:

| Variable | Default |
|----------|---------|
| `DB_HOST` | `localhost` |
| `DB_PORT` | `5433` |
| `DB_USER` | `postgres` |
| `DB_PASSWORD` | `dinesh_2006` |
| `DB_NAME` | `doctor_verification_db` |

### 2. OCR microservice

```bash
cd ocr_service
pip install -r requirements.txt
python app.py
```

Runs at `http://127.0.0.1:5001`

### 3. FastAPI backend

```bash
cd python_backend
pip install -r requirements.txt Pillow
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open: `http://127.0.0.1:8000`

OTP for registration is printed in the backend terminal via the mock SMS provider.

---

## Doctor Verification Workflow

1. Register + OTP verify  
2. Add license, qualification, clinic  
3. Upload documents (registration cert, degree, Aadhaar/PAN/Passport)  
4. **eKYC evaluation** — backend calls `ocr_service` (`/api/v1/ocr`) for OCR + face crop + ID validation, then decides `AUTO_VERIFIED` / `MANUAL_REVIEW` / `FAILED`  
5. Digital prescription studio (unlocked after Step 4 succeeds)  

> Keep both services running: FastAPI (`:8000`) and OCR (`:5001`).

---

## Docker Compose

```bash
docker compose up --build
```

- Portal/API: `http://localhost:8080`  
- OCR: `http://localhost:5001`  
- Postgres: `localhost:5432`  

---

## Configuration

Common environment variables:

- `JWT_SECRET`
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- `PORT` (backend listen port)

OCR service URL used by the backend (when wired): `http://127.0.0.1:5001/api/v1/ocr`

---

## Notes

- This repository is **Python-only**. The previous Go backend has been removed.
- Uploaded OCR test artifacts under `ocr_service/ocr_uploads/` are runtime data.
- Keep `ocr_service/FSRCNN_x2.pb` — required for PAN/Aadhaar image enhancement.
