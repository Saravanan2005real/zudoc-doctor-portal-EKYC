package events

import (
	"context"
	"encoding/json"
	"log"
)

type RabbitMQEventBus struct {
	amqpURL  string
	memoryBus *MemoryEventBus
}

func NewRabbitMQEventBus(amqpURL string) *RabbitMQEventBus {
	return &RabbitMQEventBus{
		amqpURL:   amqpURL,
		memoryBus: NewMemoryEventBus(),
	}
}

func (r *RabbitMQEventBus) Subscribe(eventType EventType, handler EventHandler) {
	r.memoryBus.Subscribe(eventType, handler)
}

func (r *RabbitMQEventBus) Publish(ctx context.Context, event Event) {
	eventBytes, err := json.Marshal(event)
	if err == nil {
		log.Printf("[RABBITMQ EVENT BUS] Serialized event payload (%d bytes) for channel '%s'", len(eventBytes), event.GetType())
	}
	r.memoryBus.Publish(ctx, event)
}
