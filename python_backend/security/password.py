"""Password hashing and validation"""
import bcrypt
import re

class PasswordUtil:
    BCRYPT_COST = 12
    
    def HashPassword(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt(rounds=self.BCRYPT_COST)
        hashed = bcrypt.hashpw(password.encode(), salt)
        return hashed.decode()
    
    def CheckPasswordHash(self, password: str, hash_str: str) -> bool:
        """Check if a password matches its hash"""
        try:
            return bcrypt.checkpw(password.encode(), hash_str.encode())
        except Exception:
            return False
    
    def ValidatePasswordPolicy(self, password: str) -> bool:
        """Validate password against policy requirements"""
        if len(password) < 8:
            raise Exception("Password must be at least 8 characters long")
        
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_number = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[^A-Za-z0-9]', password))
        
        if not has_upper:
            raise Exception("Password must contain at least one uppercase letter")
        if not has_lower:
            raise Exception("Password must contain at least one lowercase letter")
        if not has_number:
            raise Exception("Password must contain at least one digit")
        if not has_special:
            raise Exception("Password must contain at least one special character")
        
        return True
