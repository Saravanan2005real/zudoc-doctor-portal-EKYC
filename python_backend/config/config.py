from pydantic_settings import BaseSettings
from typing import Optional
from datetime import timedelta

class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: str = "5433"
    db_user: str = "postgres"
    db_password: str = "dinesh_2006"
    db_name: str = "doctor_verification_db"
    
    jwt_secret: str = "super-secret-jwt-key-2026"
    refresh_token_duration: int = 24 * 3600
    
    port: str = "8080"
    
    # OTP settings
    otp_duration_minutes: int = 10
    otp_max_attempts: int = 3
    
    # Login settings
    max_login_attempts: int = 5
    account_lock_duration_minutes: int = 30

    @property
    def database_url(self) -> str:
        return f"postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def OTPDuration(self) -> timedelta:
        return timedelta(minutes=self.otp_duration_minutes)
    
    @property
    def OTPMaxAttempts(self) -> int:
        return self.otp_max_attempts
    
    @property
    def MaxLoginAttempts(self) -> int:
        return self.max_login_attempts
    
    @property
    def AccountLockDuration(self) -> timedelta:
        return timedelta(minutes=self.account_lock_duration_minutes)

    class Config:
        env_file = ".env"

settings = Settings()