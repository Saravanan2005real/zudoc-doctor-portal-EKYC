package security_test

import (
	"context"
	"testing"
	"time"

	"doctor-service/security"
)

func TestDistributedLockAcquisitionAndRelease(t *testing.T) {
	lockMgr := security.NewDistributedLockManager(2 * time.Second)
	lockKey := security.FormatVerificationLockKey("doctor-uuid-12345")

	ctx := context.Background()

	// Acquire lock 1: Should succeed
	acquired, err := lockMgr.AcquireLock(ctx, lockKey)
	if err != nil || !acquired {
		t.Fatalf("expected lock acquisition to succeed, got acquired=%v, err=%v", acquired, err)
	}

	// Acquire lock 2 (while locked): Should fail
	acquired2, err := lockMgr.AcquireLock(ctx, lockKey)
	if acquired2 {
		t.Fatalf("expected second lock acquisition attempt to fail while held")
	}

	// Release lock
	err = lockMgr.ReleaseLock(ctx, lockKey)
	if err != nil {
		t.Fatalf("failed to release lock: %v", err)
	}

	// Re-acquire lock: Should succeed again
	acquired3, err := lockMgr.AcquireLock(ctx, lockKey)
	if err != nil || !acquired3 {
		t.Fatalf("expected re-acquisition after release to succeed")
	}
}
