package notifications

import (
	"context"

	"github.com/google/uuid"
)

type NotificationPayload struct {
	DoctorID    uuid.UUID
	Recipient   string
	Channel     string // "EMAIL", "SMS", "PUSH"
	Subject     string
	Message     string
	ActionURL   string
}

type NotificationProvider interface {
	Send(ctx context.Context, payload NotificationPayload) error
	GetProviderName() string
}
