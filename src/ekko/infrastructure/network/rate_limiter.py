"""Token bucket rate limiter providing polite per-domain pacing."""

import asyncio
import time


class TokenBucket:
    """Asynchronous token bucket maintaining rate limit and burst capacity."""

    def __init__(self, rate_per_sec: float, burst: int) -> None:
        self.rate_per_sec = rate_per_sec
        self.burst = float(burst)
        self.tokens = float(burst)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    def _replenish(self) -> None:
        """Add newly generated tokens based on elapsed monotonic time."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.burst, self.tokens + (elapsed * self.rate_per_sec))
        self.last_update = now

    async def acquire(self, tokens: float = 1.0) -> None:
        """Wait asynchronously until enough tokens are available then consume."""
        async with self._lock:
            while True:
                self._replenish()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                deficit = tokens - self.tokens
                wait_time = deficit / self.rate_per_sec
                await asyncio.sleep(wait_time)


class DomainRateLimiter:
    """Manages dedicated token buckets partitioned by domain/host."""

    def __init__(self, rate_per_sec: float = 2.0, burst: int = 5) -> None:
        self.rate_per_sec = rate_per_sec
        self.burst = burst
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()

    async def _get_bucket(self, host: str) -> TokenBucket:
        """Retrieve or create bucket for a given host safely."""
        async with self._lock:
            if host not in self._buckets:
                self._buckets[host] = TokenBucket(self.rate_per_sec, self.burst)
            return self._buckets[host]

    async def acquire(self, host: str) -> None:
        """Acquire a token for the specified host before issuing request."""
        bucket = await self._get_bucket(host)
        await bucket.acquire()
