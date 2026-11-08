import time
from collections import defaultdict
from typing import Dict, List
from fastapi import HTTPException, status, Request
from app.models.user import User
from app.models.retailer import Retailer


class InMemoryRateLimiter:
    """
    Sliding window rate limiter to protect compute-intensive AI endpoints.
    Tracks timestamps per client/retailer key.
    """

    def __init__(self, requests_limit: int = 15, window_seconds: int = 60):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self._history: Dict[str, List[float]] = defaultdict(list)

    def check_rate_limit(self, key: str) -> None:
        """
        Check if key has exceeded allowed requests within the time window.
        Raises HTTP 429 Too Many Requests if breached.
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Prune outdated timestamps
        valid_timestamps = [ts for ts in self._history[key] if ts > window_start]
        self._history[key] = valid_timestamps

        if len(valid_timestamps) >= self.requests_limit:
            retry_after = int(self.window_seconds - (now - valid_timestamps[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for AI capture ({self.requests_limit} requests per {self.window_seconds}s). Please wait before retrying.",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        self._history[key].append(now)

    def reset(self) -> None:
        """Clear all rate limit history (useful for test isolation)."""
        self._history.clear()


# Default instance: 15 requests per 60 seconds for AI capture
ai_rate_limiter = InMemoryRateLimiter(requests_limit=15, window_seconds=60)

