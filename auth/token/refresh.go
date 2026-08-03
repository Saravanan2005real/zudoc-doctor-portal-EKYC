package token

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"time"
)

type RefreshTokenManager struct {
	duration time.Duration
}

func NewRefreshTokenManager(duration time.Duration) *RefreshTokenManager {
	return &RefreshTokenManager{
		duration: duration,
	}
}

func (m *RefreshTokenManager) GenerateRefreshToken() (string, string, time.Time, error) {
	bytes := make([]byte, 32)
	if _, err := rand.Read(bytes); err != nil {
		return "", "", time.Time{}, err
	}

	rawToken := hex.EncodeToString(bytes)
	tokenHash := HashRefreshToken(rawToken)
	expiresAt := time.Now().Add(m.duration)

	return rawToken, tokenHash, expiresAt, nil
}

func HashRefreshToken(token string) string {
	hash := sha256.Sum256([]byte(token))
	return hex.EncodeToString(hash[:])
}
