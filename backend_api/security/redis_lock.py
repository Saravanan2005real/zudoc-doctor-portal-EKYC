import time
from threading import Lock
from typing import Dict

class DistributedLockManager:
    def __init__(self, ttl: float = 30.0):
        if ttl <= 0:
            ttl = 30.0
        self.mu = Lock()
        self.locks: Dict[str, float] = {}
        self.ttl = ttl

    def acquire_lock(self, context, lock_key: str) -> bool:
        with self.mu:
            expiry = self.locks.get(lock_key)
            now = time.time()

            if expiry is not None and now < expiry:
                return False

            self.locks[lock_key] = now + self.ttl
            return True

    def release_lock(self, context, lock_key: str):
        with self.mu:
            if lock_key in self.locks:
                del self.locks[lock_key]

    def is_locked(self, context, lock_key: str) -> bool:
        with self.mu:
            expiry = self.locks.get(lock_key)
            if expiry is not None and time.time() < expiry:
                return True
            return False

def format_verification_lock_key(doctor_id: str) -> str:
    return f"lock:verification:doctor:{doctor_id}"
