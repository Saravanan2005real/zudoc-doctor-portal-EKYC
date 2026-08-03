package config

import (
	"os"
	"time"
)

type Config struct {
	JWTSecret            string
	AccessTokenDuration  time.Duration
	RefreshTokenDuration time.Duration
	OTPDuration          time.Duration
	OTPMaxAttempts       int
	MaxLoginAttempts     int
	AccountLockDuration  time.Duration
	SMSProviderType      string // "MOCK", "MSG91", "TWILIO"
}

func LoadConfig() *Config {
	secret := os.Getenv("JWT_SECRET")
	if secret == "" {
		secret = "super-secret-doctor-verification-jwt-key-change-in-prod"
	}

	smsProvider := os.Getenv("SMS_PROVIDER")
	if smsProvider == "" {
		smsProvider = "MOCK"
	}

	return &Config{
		JWTSecret:            secret,
		AccessTokenDuration:  15 * time.Minute,
		RefreshTokenDuration: 30 * 24 * time.Hour,
		OTPDuration:          5 * time.Minute,
		OTPMaxAttempts:       5,
		MaxLoginAttempts:     5,
		AccountLockDuration:  15 * time.Minute,
		SMSProviderType:      smsProvider,
	}
}
