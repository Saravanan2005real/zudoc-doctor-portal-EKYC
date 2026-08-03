package security

import (
	"net/http"
	"sync"
	"time"
)

type clientLimiter struct {
	tokens     int
	maxTokens  int
	lastRefill time.Time
}

type RateLimiter struct {
	mu           sync.Mutex
	clients      map[string]*clientLimiter
	maxRequests  int
	windowPeriod time.Duration
}

func NewRateLimiter(maxRequests int, windowPeriod time.Duration) *RateLimiter {
	limiter := &RateLimiter{
		clients:      make(map[string]*clientLimiter),
		maxRequests:  maxRequests,
		windowPeriod: windowPeriod,
	}

	// Background cleanup of inactive clients
	go func() {
		for {
			time.Sleep(5 * time.Minute)
			limiter.mu.Lock()
			for ip, client := range limiter.clients {
				if time.Since(client.lastRefill) > windowPeriod*2 {
					delete(limiter.clients, ip)
				}
			}
			limiter.mu.Unlock()
		}
	}()

	return limiter
}

func (l *RateLimiter) Limit(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		clientIP := r.RemoteAddr
		if forwarded := r.Header.Get("X-Forwarded-For"); forwarded != "" {
			clientIP = forwarded
		}

		l.mu.Lock()
		client, exists := l.clients[clientIP]
		now := time.Now()

		if !exists {
			client = &clientLimiter{
				tokens:     l.maxRequests - 1,
				maxTokens:  l.maxRequests,
				lastRefill: now,
			}
			l.clients[clientIP] = client
			l.mu.Unlock()
			next.ServeHTTP(w, r)
			return
		}

		// Refill tokens based on elapsed time
		elapsed := now.Sub(client.lastRefill)
		if elapsed > l.windowPeriod {
			client.tokens = l.maxRequests
			client.lastRefill = now
		}

		if client.tokens <= 0 {
			l.mu.Unlock()
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusTooManyRequests)
			_, _ = w.Write([]byte(`{"error":"Too many requests. Please slow down and try again later."}`))
			return
		}

		client.tokens--
		l.mu.Unlock()

		next.ServeHTTP(w, r)
	})
}
