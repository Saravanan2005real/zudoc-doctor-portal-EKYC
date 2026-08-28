from threading import Lock

class MetricsCollector:
    def __init__(self):
        self.total_registrations = 0
        self.total_verifications = 0
        self.auto_approved_count = 0
        self.manual_review_count = 0
        self.rejected_count = 0
        self.active_queue_depth = 0
        self.dead_letter_queue_depth = 0
        self.mu = Lock()

    def increment_registrations(self):
        with self.mu:
            self.total_registrations += 1

    def increment_auto_approved(self):
        with self.mu:
            self.total_verifications += 1
            self.auto_approved_count += 1

    def increment_manual_review(self):
        with self.mu:
            self.total_verifications += 1
            self.manual_review_count += 1

    def increment_rejected(self):
        with self.mu:
            self.total_verifications += 1
            self.rejected_count += 1

    def serve_http(self, request):
        metrics = []
        metrics.append("# HELP doctor_registrations_total Total doctor registrations")
        metrics.append("# TYPE doctor_registrations_total counter")
        metrics.append(f"doctor_registrations_total {self.total_registrations}\n")

        metrics.append("# HELP doctor_verifications_total Total verifications completed")
        metrics.append("# TYPE doctor_verifications_total counter")
        metrics.append(f"doctor_verifications_total {self.total_verifications}\n")

        metrics.append("# HELP doctor_auto_approved_total Total auto-approved verifications")
        metrics.append("# TYPE doctor_auto_approved_total counter")
        metrics.append(f"doctor_auto_approved_total {self.auto_approved_count}\n")

        metrics.append("# HELP doctor_manual_review_total Total manual review verifications")
        metrics.append("# TYPE doctor_manual_review_total counter")
        metrics.append(f"doctor_manual_review_total {self.manual_review_count}\n")

        metrics.append("# HELP doctor_rejected_total Total rejected verifications")
        metrics.append("# TYPE doctor_rejected_total counter")
        metrics.append(f"doctor_rejected_total {self.rejected_count}\n")

        metrics.append("# HELP verification_queue_depth Current queue depth")
        metrics.append("# TYPE verification_queue_depth gauge")
        metrics.append(f"verification_queue_depth {self.active_queue_depth}\n")

        metrics.append("# HELP dead_letter_queue_depth DLQ depth")
        metrics.append("# TYPE dead_letter_queue_depth gauge")
        metrics.append(f"dead_letter_queue_depth {self.dead_letter_queue_depth}")

        return "\n".join(metrics), 200, {"Content-Type": "text/plain; version=0.0.4"}

GlobalMetrics = MetricsCollector()
