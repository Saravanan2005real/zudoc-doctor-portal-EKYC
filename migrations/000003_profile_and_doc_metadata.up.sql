-- Add Profile fields to doctors table
ALTER TABLE doctors 
ADD COLUMN IF NOT EXISTS languages VARCHAR(255),
ADD COLUMN IF NOT EXISTS biography TEXT;

-- Add document metadata fields to doctor_documents table
ALTER TABLE doctor_documents
ADD COLUMN IF NOT EXISTS original_filename VARCHAR(255) NOT NULL DEFAULT 'document.pdf',
ADD COLUMN IF NOT EXISTS file_size BIGINT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64) NOT NULL DEFAULT '',
ADD COLUMN IF NOT EXISTS resolution_width INT,
ADD COLUMN IF NOT EXISTS resolution_height INT;

-- Index for duplicate file check per doctor
CREATE INDEX IF NOT EXISTS idx_doc_hash ON doctor_documents(doctor_id, file_hash);
