-- Immutable Audit Events Table
CREATE TABLE IF NOT EXISTS audit_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_type VARCHAR(50) NOT NULL,
    actor_id UUID NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    before_state JSONB,
    after_state JSONB,
    ip_address VARCHAR(50),
    device TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Dead Letter Queue (DLQ) Jobs Table
CREATE TABLE IF NOT EXISTS verification_dead_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL,
    doctor_id UUID NOT NULL,
    failure_reason TEXT NOT NULL,
    retry_count INT NOT NULL DEFAULT 0,
    payload_json JSONB,
    failed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Digital Prescriptions Table
CREATE TABLE IF NOT EXISTS prescriptions (
    prescription_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    patient_id VARCHAR(100) NOT NULL,
    diagnosis TEXT NOT NULL,
    medicines JSONB NOT NULL,
    digital_signature TEXT NOT NULL,
    qr_payload TEXT NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_events(actor_type, actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events(action);
CREATE INDEX IF NOT EXISTS idx_dlq_doctor ON verification_dead_jobs(doctor_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_doctor ON prescriptions(doctor_id);
