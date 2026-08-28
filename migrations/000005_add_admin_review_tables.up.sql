-- Add DOCUMENTS_REQUESTED to doctor_status_enum
ALTER TYPE doctor_status_enum ADD VALUE IF NOT EXISTS 'DOCUMENTS_REQUESTED';

-- Add assignment and prescription authorization columns to doctors
ALTER TABLE doctors
ADD COLUMN IF NOT EXISTS assigned_admin_id UUID REFERENCES admin_users(admin_id),
ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS prescription_enabled BOOLEAN NOT NULL DEFAULT FALSE;

-- Table for Admin Audit Actions
CREATE TABLE IF NOT EXISTS admin_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL REFERENCES admin_users(admin_id),
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    previous_status VARCHAR(50) NOT NULL,
    new_status VARCHAR(50) NOT NULL,
    reason TEXT,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table for Doctor Internal/Public Notes
CREATE TABLE IF NOT EXISTS doctor_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    admin_id UUID NOT NULL REFERENCES admin_users(admin_id),
    note TEXT NOT NULL,
    visibility VARCHAR(50) NOT NULL DEFAULT 'INTERNAL',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table for Verification Flags & Issues
CREATE TABLE IF NOT EXISTS verification_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    flag_type VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL DEFAULT 'MEDIUM',
    message TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_by UUID REFERENCES admin_users(admin_id),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_admin_actions_doctor ON admin_actions(doctor_id);
CREATE INDEX IF NOT EXISTS idx_admin_actions_admin ON admin_actions(admin_id);
CREATE INDEX IF NOT EXISTS idx_doctor_notes_doctor ON doctor_notes(doctor_id);
CREATE INDEX IF NOT EXISTS idx_vflags_doctor ON verification_flags(doctor_id);
