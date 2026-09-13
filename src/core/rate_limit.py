"""In-process sliding-window rate limiter for login attempts.

Counts FAILED logins per username. When a username accumulates
LOGIN_MAX_FAILED_ATTEMPTS failures inside LOGIN_WINDOW_SECONDS, further
login attempts for that username are rejected until the window's oldest
failure ages out. A successful login clears that username's history.

In-memory by design: the API runs as a single process (SQLite, one host),
so no external store is required. If multiple workers or instances are
ever deployed, swap the dict backend for Redis -- the class interface
stays the same.

Framework-agnostic on purpose (like the rest of src/core): callers decide
how to turn is_blocked()/retry_after_seconds() into an HTTP response.
"""

import threading
import time
from collections import deque

from src.core.config import get_settings


class SlidingWindowLimiter:
    """Per-key sliding window of failure timestamps (thread-safe)."""

    def __init__(self, max_attempts: int, window_seconds: float):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, attempts: deque[float], now: float) -> None:
        """Drop timestamps older than the window (caller holds the lock)."""
        while attempts and now - attempts[0] > self.window_seconds:
            attempts.popleft()

    def is_blocked(self, key: str) -> bool:
        """True when the key has reached max_attempts inside the window."""
        now = time.monotonic()
        with self._lock:
            attempts = self._attempts.get(key)
            if attempts is None:
                return False
            self._prune(attempts, now)
            if not attempts:
                del self._attempts[key]
                return False
            return len(attempts) >= self.max_attempts

    def retry_after_seconds(self, key: str) -> float:
        """Seconds until the key may try again; 0.0 when not blocked."""
        now = time.monotonic()
        with self._lock:
            attempts = self._attempts.get(key)
            if attempts is None:
                return 0.0
            self._prune(attempts, now)
            if len(attempts) < self.max_attempts:
                return 0.0
            oldest = attempts[0]
            return max(0.0, self.window_seconds - (now - oldest))

    def record_failure(self, key: str) -> None:
        """Register one failed attempt for the key."""
        now = time.monotonic()
        with self._lock:
            self._attempts.setdefault(key, deque()).append(now)

    def record_success(self, key: str) -> None:
        """Clear the key's history after a successful attempt."""
        with self._lock:
            self._attempts.pop(key, None)


settings = get_settings()
login_limiter = SlidingWindowLimiter(
    max_attempts=settings.LOGIN_MAX_FAILED_ATTEMPTS,
    window_seconds=settings.LOGIN_WINDOW_SECONDS,
)