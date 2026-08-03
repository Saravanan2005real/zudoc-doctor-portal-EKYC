package events

import (
	"context"
	"log"
	"sync"
)

type EventHandler func(ctx context.Context, event Event) error

type EventBus interface {
	Subscribe(eventType EventType, handler EventHandler)
	Publish(ctx context.Context, event Event)
}

type MemoryEventBus struct {
	mu       sync.RWMutex
	handlers map[EventType][]EventHandler
}

func NewMemoryEventBus() *MemoryEventBus {
	return &MemoryEventBus{
		handlers: make(map[EventType][]EventHandler),
	}
}

func (b *MemoryEventBus) Subscribe(eventType EventType, handler EventHandler) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.handlers[eventType] = append(b.handlers[eventType], handler)
	log.Printf("[EVENT BUS] Subscribed handler to event '%s'", eventType)
}

func (b *MemoryEventBus) Publish(ctx context.Context, event Event) {
	b.mu.RLock()
	handlers, exists := b.handlers[event.GetType()]
	b.mu.RUnlock()

	if !exists || len(handlers) == 0 {
		return
	}

	log.Printf("[EVENT BUS] Publishing Event '%s' for Doctor '%s'", event.GetType(), event.GetDoctorID())

	for _, handler := range handlers {
		// Non-blocking async event dispatch
		go func(h EventHandler) {
			if err := h(ctx, event); err != nil {
				log.Printf("[EVENT BUS] Error handling event '%s': %v", event.GetType(), err)
			}
		}(handler)
	}
}
