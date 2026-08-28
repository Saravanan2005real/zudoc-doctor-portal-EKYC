"""OTP generation and verification"""
import secrets
import hashlib

class OTPUtil:
    def GenerateSecureOTP(self, length: int = 6) -> str:
        """Generate a secure random OTP"""
        if length <= 0:
            length = 6
        
        # Generate a random number with the specified length
        otp = ''.join([str(secrets.randbelow(10)) for _ in range(length)])
        return otp.zfill(length)
    
    def HashOTP(self, otp: str) -> str:
        """Hash an OTP using SHA-256"""
        hash_obj = hashlib.sha256(otp.encode())
        return hash_obj.hexdigest()
    
    def VerifyOTP(self, otp: str, hashed_otp: str) -> bool:
        """Verify an OTP against its hash"""
        return self.HashOTP(otp) == hashed_otp
