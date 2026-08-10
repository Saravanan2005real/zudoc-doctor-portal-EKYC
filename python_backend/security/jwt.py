"""JWT token management"""
import jwt
from datetime import datetime, timedelta
from uuid import UUID
from typing import Tuple

class JWTManager:
    def __init__(self, secret_key: str, token_duration_minutes: int):
        self.secret_key = secret_key
        self.token_duration = timedelta(minutes=token_duration_minutes)
    
    def GenerateToken(self, doctor_id, public_id, email: str, role: str) -> Tuple[str, datetime]:
        """Generate a JWT token"""
        expires_at = datetime.utcnow() + self.token_duration
        
        payload = {
            'doctor_id': str(doctor_id),
            'public_id': str(public_id),
            'email': email,
            'role': role,
            'exp': expires_at,
            'iat': datetime.utcnow(),
            'sub': str(public_id)
        }
        
        token_str = jwt.encode(payload, self.secret_key, algorithm='HS256')
        return token_str, expires_at
    
    def ValidateToken(self, token_str: str) -> dict:
        """Validate and decode a JWT token"""
        try:
            payload = jwt.decode(token_str, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            raise Exception("Token has expired")
        except jwt.InvalidTokenError:
            raise Exception("Invalid token")
