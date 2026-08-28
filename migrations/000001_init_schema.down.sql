DROP TABLE IF EXISTS verification_history CASCADE;
DROP TABLE IF EXISTS doctor_documents CASCADE;
DROP TABLE IF EXISTS doctor_clinics CASCADE;
DROP TABLE IF EXISTS doctor_qualifications CASCADE;
DROP TABLE IF EXISTS doctor_licenses CASCADE;
DROP TABLE IF EXISTS doctors CASCADE;
DROP TABLE IF EXISTS admin_users CASCADE;

DROP TYPE IF EXISTS admin_role_enum;
DROP TYPE IF EXISTS ocr_status_enum;
DROP TYPE IF EXISTS document_type_enum;
DROP TYPE IF EXISTS consultation_mode_enum;
DROP TYPE IF EXISTS verification_status_enum;
DROP TYPE IF EXISTS doctor_status_enum;
