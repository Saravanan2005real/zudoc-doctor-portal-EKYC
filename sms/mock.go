package sms

import (
	"context"
	"fmt"
	"log"
)

type MockSMSProvider struct{}

func NewMockSMSProvider() *MockSMSProvider {
	return &MockSMSProvider{}
}

func (m *MockSMSProvider) SendOTP(ctx context.Context, payload SMSPayload) error {
	log.Printf("[MOCK SMS PROVIDER] Sending OTP '%s' to mobile '%s' for purpose '%s'", payload.OTP, payload.Mobile, payload.Purpose)
	fmt.Printf("\n=======================================================\n")
	fmt.Printf("[MOCK SMS] Mobile: %s | OTP: %s | Purpose: %s\n", payload.Mobile, payload.OTP, payload.Purpose)
	fmt.Printf("=======================================================\n\n")
	return nil
}

func (m *MockSMSProvider) GetProviderName() string {
	return "MOCK"
}
