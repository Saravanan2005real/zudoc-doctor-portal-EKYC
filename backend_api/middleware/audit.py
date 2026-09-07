from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import threading
from database import SessionLocal
from entities.audit_log import AuditLog
from security.auth import decode_token

class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # We only want to audit modifying actions
        if request.method not in ["POST", "PUT", "DELETE"]:
            return await call_next(request)

        # Proceed with the request
        response = await call_next(request)

        # Only audit successful operations (or whatever our compliance requires)
        if 200 <= response.status_code < 300:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                if payload and "sub" in payload:
                    actor_id = int(payload["sub"])
                    
                    # Fire and forget auditing in background thread
                    thread = threading.Thread(
                        target=self._log_audit,
                        args=(actor_id, request.method, str(request.url.path), request.client.host)
                    )
                    thread.start()
        
        return response

    def _log_audit(self, actor_id: int, method: str, path: str, ip_address: str):
        db = SessionLocal()
        try:
            log = AuditLog(
                actor_id=actor_id,
                action=f"{method} {path}",
                resource_type="API_ROUTE",
                ip_address=ip_address,
                metadata_info={"path": path, "method": method}
            )
            db.add(log)
            db.commit()
        finally:
            db.close()
