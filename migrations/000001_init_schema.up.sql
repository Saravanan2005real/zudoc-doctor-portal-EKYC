-- Enable UUID Extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Custom Enums
CREATE TYPE doctor_status_enum AS ENUM (
    'NOT_SUBMITTED',
    'PENDING',
    'AUTO_VERIFIED',
    'MANUAL_REVIEW',
    'VERIFIED', 
    'REJECTED', 
    'SUSPENDED'
);

CREATE TYPE verification_status_enum AS ENUM (
    'UNVERIFIED', 
    'PENDING', 
    'VERIFIED', 
    'REJECTED'
);

CREATE TYPE consultation_mode_enum AS ENUM (
    'ONLINE', 
    'OFFLINE', 
    'BOTH'
);

CREATE TYPE document_type_enum AS ENUM (
    'AADHAAR', 
    'PAN', 
    'PASSPORT', 
    'REGISTRATION_CERTIFICATE', 
    'MBBS_CERTIFICATE', 
    'MD_CERTIFICATE', 
    'PHOTO'
);

CREATE TYPE ocr_status_enum AS ENUM (
    'PENDING', 
    'PROCESSING', 
    'COMPLETED', 
    'FAILED'
);

CREATE TYPE admin_role_enum AS ENUM (
    'REVIEWER', 
    'SENIOR_REVIEWER', 
    'SUPER_ADMIN'
);

-- 1. Doctors Table
CREATE TABLE IF NOT EXISTS doctors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    gender VARCHAR(20),
    dob DATE,
    mobile VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    profile_photo TEXT,
    status doctor_status_enum NOT NULL DEFAULT 'NOT_SUBMITTED',
    fraud_score INT DEFAULT 0 CHECK (fraud_score >= 0 AND fraud_score <= 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID
);

-- 2. Doctor Licenses Table
CREATE TABLE IF NOT EXISTS doctor_licenses (
    license_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    registration_number VARCHAR(100) NOT NULL,
    registration_council VARCHAR(255) NOT NULL,
    registration_year INT NOT NULL,
    issue_date DATE,
    expiry_date DATE,
    license_status VARCHAR(50) DEFAULT 'ACTIVE',
    verification_status verification_status_enum NOT NULL DEFAULT 'UNVERIFIED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

-- 3. Doctor Qualifications Table
CREATE TABLE IF NOT EXISTS doctor_qualifications (
    qualification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    degree VARCHAR(100) NOT NULL,
    specialization VARCHAR(150),
    college VARCHAR(255) NOT NULL,
    university VARCHAR(255) NOT NULL,
    year_completed INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

-- 4. Doctor Clinics Table
CREATE TABLE IF NOT EXISTS doctor_clinics (
    clinic_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    clinic_name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pincode VARCHAR(20) NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    consultation_mode consultation_mode_enum NOT NULL DEFAULT 'OFFLINE',
    consultation_fee DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

-- 5. Doctor Documents Table (with versioning & raw OCR JSON)
CREATE TABLE IF NOT EXISTS doctor_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    document_type document_type_enum NOT NULL,
    file_url TEXT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    version INT NOT NULL DEFAULT 1,
    is_latest BOOLEAN NOT NULL DEFAULT TRUE,
    ocr_status ocr_status_enum NOT NULL DEFAULT 'PENDING',
    ocr_text TEXT,
    ocr_raw_json JSONB,
    ocr_confidence DECIMAL(5, 2),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

-- 6. Verification History Table
CREATE TABLE IF NOT EXISTS verification_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    remarks TEXT,
    performed_by UUID,
    performed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 7. Admin Users Table
CREATE TABLE IF NOT EXISTS admin_users (
    admin_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role admin_role_enum NOT NULL DEFAULT 'REVIEWER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_doctors_public_id ON doctors(public_id);
CREATE INDEX IF NOT EXISTS idx_doctors_mobile ON doctors(mobile);
CREATE INDEX IF NOT EXISTS idx_doctors_email ON doctors(email);
CREATE INDEX IF NOT EXISTS idx_doctors_status ON doctors(status);
CREATE INDEX IF NOT EXISTS idx_doctors_deleted_at ON doctors(deleted_at);

CREATE INDEX IF NOT EXISTS idx_licenses_doctor_id ON doctor_licenses(doctor_id);
CREATE INDEX IF NOT EXISTS idx_licenses_reg_no ON doctor_licenses(registration_number);

CREATE INDEX IF NOT EXISTS idx_qualifications_doctor_id ON doctor_qualifications(doctor_id);

CREATE INDEX IF NOT EXISTS idx_clinics_doctor_id ON doctor_clinics(doctor_id);
CREATE INDEX IF NOT EXISTS idx_clinics_city_state ON doctor_clinics(city, state);

CREATE INDEX IF NOT EXISTS idx_documents_doctor_id ON doctor_documents(doctor_id);
CREATE INDEX IF NOT EXISTS idx_documents_type_latest ON doctor_documents(doctor_id, document_type, is_latest);

CREATE INDEX IF NOT EXISTS idx_history_doctor_id ON verification_history(doctor_id);

CREATE INDEX IF NOT EXISTS idx_admin_email ON admin_users(email);
