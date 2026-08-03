package sms

import "context"

type SMSPayload struct {
	Mobile  string
	OTP     string
	Purpose string
	Message string
}

type SMSProvider interface {
	SendOTP(ctx context.Context, payload SMSPayload) error
	GetProviderName() string
}
