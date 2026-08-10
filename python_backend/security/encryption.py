import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class FieldEncryptor:
    def __init__(self, hex_key=None):
        if not hex_key:
            hex_key = "6361666562616265313233343536373839303132333435363738393031323334"
            
        try:
            self.secret_key = bytes.fromhex(hex_key)
            if len(self.secret_key) != 32:
                raise ValueError
        except ValueError:
            raise ValueError("encryption key must be a valid 64-character hex string (32 bytes / 256 bits)")
            
    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
            
        aesgcm = AESGCM(self.secret_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        return (nonce + ciphertext).hex()

    def decrypt(self, ciphertext_hex: str) -> str:
        if not ciphertext_hex:
            return ""
            
        try:
            data = bytes.fromhex(ciphertext_hex)
        except ValueError as e:
            raise ValueError(f"invalid ciphertext hex: {e}")
            
        if len(data) < 12:
            raise ValueError("ciphertext too short")
            
        nonce = data[:12]
        ciphertext = data[12:]
        
        aesgcm = AESGCM(self.secret_key)
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise ValueError(f"decryption authentication failed: {e}")
            
        return plaintext.decode('utf-8')
