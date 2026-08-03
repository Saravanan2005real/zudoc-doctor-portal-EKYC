-- Table for Verification Background Jobs
CREATE TABLE IF NOT EXISTS verification_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'QUEUED',
    priority INT NOT NULL DEFAULT 1,
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 3,
    last_error TEXT,
    payload_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Table for Document OCR Results
CREATE TABLE IF NOT EXISTS document_ocr_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES doctor_documents(document_id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    raw_json JSONB NOT NULL,
    parsed_json JSONB NOT NULL,
    confidence DECIMAL(5, 2) NOT NULL,
    processing_time_ms BIGINT NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_vjobs_status_priority ON verification_jobs(status, priority DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_vjobs_doctor_id ON verification_jobs(doctor_id);
CREATE INDEX IF NOT EXISTS idx_ocr_results_doc_id ON document_ocr_results(document_id);
