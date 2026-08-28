DROP TABLE IF EXISTS verification_flags CASCADE;
DROP TABLE IF EXISTS doctor_notes CASCADE;
DROP TABLE IF EXISTS admin_actions CASCADE;

ALTER TABLE doctors
DROP COLUMN IF EXISTS prescription_enabled,
DROP COLUMN IF EXISTS assigned_at,
DROP COLUMN IF EXISTS assigned_admin_id;
