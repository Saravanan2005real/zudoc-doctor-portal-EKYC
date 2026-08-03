package observability

import (
	"fmt"
	"net/http"
	"sync/atomic"
)

type MetricsCollector struct {
	TotalRegistrations   int64
	TotalVerifications   int64
	AutoApprovedCount    int64
	ManualReviewCount    int64
	RejectedCount        int64
	ActiveQueueDepth     int64
	DeadLetterQueueDepth int64
}

var GlobalMetrics = &MetricsCollector{}

func (m *MetricsCollector) IncrementRegistrations() {
	atomic.AddInt64(&m.TotalRegistrations, 1)
}

func (m *MetricsCollector) IncrementAutoApproved() {
	atomic.AddInt64(&m.TotalVerifications, 1)
	atomic.AddInt64(&m.AutoApprovedCount, 1)
}

func (m *MetricsCollector) IncrementManualReview() {
	atomic.AddInt64(&m.TotalVerifications, 1)
	atomic.AddInt64(&m.ManualReviewCount, 1)
}

func (m *MetricsCollector) IncrementRejected() {
	atomic.AddInt64(&m.TotalVerifications, 1)
	atomic.AddInt64(&m.RejectedCount, 1)
}

func (m *MetricsCollector) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	w.WriteHeader(http.StatusOK)

	fmt.Fprintf(w, "# HELP doctor_registrations_total Total doctor registrations\n")
	fmt.Fprintf(w, "# TYPE doctor_registrations_total counter\n")
	fmt.Fprintf(w, "doctor_registrations_total %d\n\n", atomic.LoadInt64(&m.TotalRegistrations))

	fmt.Fprintf(w, "# HELP doctor_verifications_total Total verifications completed\n")
	fmt.Fprintf(w, "# TYPE doctor_verifications_total counter\n")
	fmt.Fprintf(w, "doctor_verifications_total %d\n\n", atomic.LoadInt64(&m.TotalVerifications))

	fmt.Fprintf(w, "# HELP doctor_auto_approved_total Total auto-approved verifications\n")
	fmt.Fprintf(w, "# TYPE doctor_auto_approved_total counter\n")
	fmt.Fprintf(w, "doctor_auto_approved_total %d\n\n", atomic.LoadInt64(&m.AutoApprovedCount))

	fmt.Fprintf(w, "# HELP doctor_manual_review_total Total manual review verifications\n")
	fmt.Fprintf(w, "# TYPE doctor_manual_review_total counter\n")
	fmt.Fprintf(w, "doctor_manual_review_total %d\n\n", atomic.LoadInt64(&m.ManualReviewCount))

	fmt.Fprintf(w, "# HELP doctor_rejected_total Total rejected verifications\n")
	fmt.Fprintf(w, "# TYPE doctor_rejected_total counter\n")
	fmt.Fprintf(w, "doctor_rejected_total %d\n\n", atomic.LoadInt64(&m.RejectedCount))

	fmt.Fprintf(w, "# HELP verification_queue_depth Current queue depth\n")
	fmt.Fprintf(w, "# TYPE verification_queue_depth gauge\n")
	fmt.Fprintf(w, "verification_queue_depth %d\n\n", atomic.LoadInt64(&m.ActiveQueueDepth))

	fmt.Fprintf(w, "# HELP dead_letter_queue_depth DLQ depth\n")
	fmt.Fprintf(w, "# TYPE dead_letter_queue_depth gauge\n")
	fmt.Fprintf(w, "dead_letter_queue_depth %d\n", atomic.LoadInt64(&m.DeadLetterQueueDepth))
}
