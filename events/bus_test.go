package events_test

import (
	"context"
	"sync"
	"testing"
	"time"

	"doctor-service/events"

	"github.com/google/uuid"
)

func TestEventBusPubSubDelivery(t *testing.T) {
	bus := events.NewMemoryEventBus()
	docID := uuid.New()

	var wg sync.WaitGroup
	wg.Add(1)

	var receivedEvent events.Event

	bus.Subscribe(events.EventTypeDoctorRegistered, func(ctx context.Context, event events.Event) error {
		defer wg.Done()
		receivedEvent = event
		return nil
	})

	bus.Publish(context.Background(), events.DoctorRegisteredEvent{
		BaseEvent: events.BaseEvent{
			Type:      events.EventTypeDoctorRegistered,
			DoctorID:  docID,
			Timestamp: time.Now(),
		},
		Email:  "doctor@example.com",
		Mobile: "9876543210",
	})

	done := make(chan struct{})
	go func() {
		wg.Wait()
		close(done)
	}()

	select {
	case <-done:
		if receivedEvent.GetDoctorID() != docID {
			t.Fatalf("expected doctor ID %s, got %s", docID, receivedEvent.GetDoctorID())
		}
	case <-time.After(2 * time.Second):
		t.Fatalf("event handler timed out")
	}
}
