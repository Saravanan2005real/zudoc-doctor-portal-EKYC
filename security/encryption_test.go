package security_test

import (
	"testing"

	"doctor-service/security"
)

func TestAES256GCMEncryptionDecryption(t *testing.T) {
	encryptor, err := security.NewFieldEncryptor("")
	if err != nil {
		t.Fatalf("failed to initialize encryptor: %v", err)
	}

	sensitiveData := "AADHAAR-9999-8888-7777-CONFIDENTIAL"
	ciphertext, err := encryptor.Encrypt(sensitiveData)
	if err != nil {
		t.Fatalf("encryption failed: %v", err)
	}

	if ciphertext == sensitiveData || len(ciphertext) == 0 {
		t.Fatalf("expected non-empty ciphertext different from plaintext")
	}

	plaintext, err := encryptor.Decrypt(ciphertext)
	if err != nil {
		t.Fatalf("decryption failed: %v", err)
	}

	if plaintext != sensitiveData {
		t.Fatalf("decrypted text '%s' does not match original plaintext '%s'", plaintext, sensitiveData)
	}
}
