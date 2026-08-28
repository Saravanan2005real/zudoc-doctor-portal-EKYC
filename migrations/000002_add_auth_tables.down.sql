DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS otp_verifications CASCADE;

ALTER TABLE doctors 
DROP COLUMN IF EXISTS password_changed_at,
DROP COLUMN IF EXISTS account_locked_until,
DROP COLUMN IF EXISTS failed_login_attempts,
DROP COLUMN IF EXISTS last_login_at,
DROP COLUMN IF EXISTS email_verified,
DROP COLUMN IF EXISTS mobile_verified;
