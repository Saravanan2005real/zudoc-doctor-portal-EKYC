"""Refresh token management"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Tuple

class RefreshTokenManager:
    def __init__(self, duration_days: int):
        self.duration = timedelta(days=duration_days)
    
    def GenerateRefreshToken(self) -> Tuple[str, str, datetime]:
        """Generate a refresh token and its hash"""
        # Generate 32 random bytes
        raw_token = secrets.token_hex(32)
        
        # Hash the token
        token_hash = self.HashRefreshToken(raw_token)
        
        # Calculate expiration
        expires_at = datetime.utcnow() + self.duration
        
        return raw_token, token_hash, expires_at
    
    def HashRefreshToken(self, token: str) -> str:
        """Hash a refresh token using SHA-256"""
        hash_obj = hashlib.sha256(token.encode())
        return hash_obj.hexdigest()
