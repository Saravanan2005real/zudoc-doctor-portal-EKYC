package security

import (
	"context"
	"fmt"
	"sync"
	"time"
)

type DistributedLockManager struct {
	mu     sync.Mutex
	locks  map[string]time.Time
	ttl    time.Duration
}

func NewDistributedLockManager(ttl time.Duration) *DistributedLockManager {
	if ttl <= 0 {
		ttl = 30 * time.Second
	}
	return &DistributedLockManager{
		locks: make(map[string]time.Time),
		ttl:   ttl,
	}
}

func (m *DistributedLockManager) AcquireLock(ctx context.Context, lockKey string) (bool, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	expiry, exists := m.locks[lockKey]
	now := time.Now()

	// If lock exists and hasn't expired, acquisition fails
	if exists && now.Before(expiry) {
		return false, nil
	}

	// Acquire lock with TTL
	m.locks[lockKey] = now.Add(m.ttl)
	return true, nil
}

func (m *DistributedLockManager) ReleaseLock(ctx context.Context, lockKey string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.locks, lockKey)
	return nil
}

func (m *DistributedLockManager) IsLocked(ctx context.Context, lockKey string) bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	expiry, exists := m.locks[lockKey]
	return exists && time.Now().Before(expiry)
}

func FormatVerificationLockKey(doctorID string) string {
	return fmt.Sprintf("lock:verification:doctor:%s", doctorID)
}
