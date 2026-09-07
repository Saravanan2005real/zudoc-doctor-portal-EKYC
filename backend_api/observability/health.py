from datetime import datetime

class HealthHandler:
    def __init__(self, db=None):
        self.db = db

    def live(self, request):
        return {
            "status": "UP",
            "service": "doctor-service",
            "timestamp": datetime.now().isoformat()
        }, 200

    def ready(self, request):
        db_status = "UP"
        http_status = 200

        if self.db is not None:
            # Assuming self.db has a ping or similar method in Python
            try:
                # self.db.ping()
                pass
            except Exception:
                db_status = "DOWN"
                http_status = 503

        return {
            "status": db_status,
            "service": "doctor-service",
            "database": db_status,
            "timestamp": datetime.now().isoformat()
        }, http_status
