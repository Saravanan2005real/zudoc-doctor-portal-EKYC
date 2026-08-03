package notifications

import (
	"context"
	"fmt"
	"log"
)

type MockNotificationProvider struct{}

func NewMockNotificationProvider() *MockNotificationProvider {
	return &MockNotificationProvider{}
}

func (m *MockNotificationProvider) Send(ctx context.Context, payload NotificationPayload) error {
	log.Printf("[NOTIFICATION SERVICE] [%s] Sending to %s | Subject: %s | Message: %s | ActionURL: %s",
		payload.Channel, payload.Recipient, payload.Subject, payload.Message, payload.ActionURL)
	fmt.Printf("\n=======================================================\n")
	fmt.Printf("[NOTIFICATION: %s] Recipient: %s\nSubject: %s\nMessage: %s\nAction URL: %s\n",
		payload.Channel, payload.Recipient, payload.Subject, payload.Message, payload.ActionURL)
	fmt.Printf("=======================================================\n\n")
	return nil
}

func (m *MockNotificationProvider) GetProviderName() string {
	return "MOCK_NOTIFICATION_PROVIDER"
}
