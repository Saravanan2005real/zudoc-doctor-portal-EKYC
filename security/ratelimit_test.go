package security_test

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"doctor-service/security"
)

func TestTokenBucketRateLimiting(t *testing.T) {
	limiter := security.NewRateLimiter(2, 1*time.Minute)

	handler := limiter.Limit(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	// Request 1: Allowed
	req1 := httptest.NewRequest(http.MethodGet, "/api/v1/doctors/profile", nil)
	req1.RemoteAddr = "192.168.1.100:12345"
	rec1 := httptest.NewRecorder()
	handler.ServeHTTP(rec1, req1)
	if rec1.Code != http.StatusOK {
		t.Fatalf("expected HTTP 200 OK on first request, got %d", rec1.Code)
	}

	// Request 2: Allowed
	req2 := httptest.NewRequest(http.MethodGet, "/api/v1/doctors/profile", nil)
	req2.RemoteAddr = "192.168.1.100:12345"
	rec2 := httptest.NewRecorder()
	handler.ServeHTTP(rec2, req2)
	if rec2.Code != http.StatusOK {
		t.Fatalf("expected HTTP 200 OK on second request, got %d", rec2.Code)
	}

	// Request 3: Exceeds limit -> 429 Too Many Requests
	req3 := httptest.NewRequest(http.MethodGet, "/api/v1/doctors/profile", nil)
	req3.RemoteAddr = "192.168.1.100:12345"
	rec3 := httptest.NewRecorder()
	handler.ServeHTTP(rec3, req3)
	if rec3.Code != http.StatusTooManyRequests {
		t.Fatalf("expected HTTP 429 Too Many Requests on third request, got %d", rec3.Code)
	}
}
