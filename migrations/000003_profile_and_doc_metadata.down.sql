ALTER TABLE doctor_documents
DROP COLUMN IF EXISTS resolution_height,
DROP COLUMN IF EXISTS resolution_width,
DROP COLUMN IF EXISTS file_hash,
DROP COLUMN IF EXISTS file_size,
DROP COLUMN IF EXISTS original_filename;

ALTER TABLE doctors 
DROP COLUMN IF EXISTS biography,
DROP COLUMN IF EXISTS languages;
