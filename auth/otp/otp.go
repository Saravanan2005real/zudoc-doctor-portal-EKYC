package otp

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"math/big"
)

func GenerateSecureOTP(length int) (string, error) {
	if length <= 0 {
		length = 6
	}

	maxVal := big.NewInt(10)
	maxVal.Exp(maxVal, big.NewInt(int64(length)), nil)

	n, err := rand.Int(rand.Reader, maxVal)
	if err != nil {
		return "", err
	}

	format := fmt.Sprintf("%%0%dd", length)
	return fmt.Sprintf(format, n.Int64()), nil
}

func HashOTP(otp string) string {
	hash := sha256.Sum256([]byte(otp))
	return hex.EncodeToString(hash[:])
}

func VerifyOTP(otp, hashedOTP string) bool {
	return HashOTP(otp) == hashedOTP
}
