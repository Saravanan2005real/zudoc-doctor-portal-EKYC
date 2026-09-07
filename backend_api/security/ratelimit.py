import time
from threading import Lock
from typing import Dict

class ClientLimiter:
    def __init__(self, max_tokens: int):
        self.tokens = max_tokens - 1
        self.max_tokens = max_tokens
        self.last_refill = time.time()

class RateLimiter:
    def __init__(self, max_requests: int, window_period: float):
        self.mu = Lock()
        self.clients: Dict[str, ClientLimiter] = {}
        self.max_requests = max_requests
        self.window_period = window_period

    def limit(self, request, next_handler):
        client_ip = request.remote_addr
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded

        with self.mu:
            client = self.clients.get(client_ip)
            now = time.time()

            if not client:
                client = ClientLimiter(self.max_requests)
                self.clients[client_ip] = client
                return next_handler(request)

            elapsed = now - client.last_refill
            if elapsed > self.window_period:
                client.tokens = self.max_requests
                client.last_refill = now

            if client.tokens <= 0:
                return {"error": "Too many requests. Please slow down and try again later."}, 429

            client.tokens -= 1

        return next_handler(request)
