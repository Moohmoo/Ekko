"""Resilient HTTP client providing polite polling, SSRF safety, and retry backoff."""

import asyncio
from dataclasses import dataclass
import random
from types import TracebackType
from typing import Mapping
from urllib.parse import urlparse
import httpx

from ekko.core.errors import EkkoError
from ekko.domains.ingestion.rate_limiter import DomainRateLimiter
from ekko.domains.ingestion.ssrf import SSRFValidator
from ekko.logger import get_logger

logger = get_logger("domains.ingestion.client")

DEFAULT_USER_AGENT = "EkkoAgent/2.0 (+https://github.com/ekko-org/ekko; polite-ingestion)"
HttpQueryParamValue = str | int | float | bool | list[str | int | float | bool]


class HttpFetchError(EkkoError):
    """Network failure after exhausting transient retry backoff attempts."""


@dataclass(frozen=True)
class HttpResponseResult:
    """Normalized response payload holding conditional cache headers."""

    status_code: int
    not_modified: bool
    text: str
    etag: str | None = None
    last_modified: str | None = None
    headers: dict[str, str] | None = None


class ResilientHttpClient:
    """HTTP client with strict SSRF filtering, domain rate limiting, and polite polling."""

    def __init__(
        self,
        rate_per_sec: float = 2.0,
        burst: int = 5,
        max_retries: int = 3,
        base_backoff: float = 0.5,
        jitter: float = 0.2,
        timeout: float = 10.0,
    ) -> None:
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.jitter = jitter
        self.ssrf_validator = SSRFValidator()
        self.rate_limiter = DomainRateLimiter(rate_per_sec=rate_per_sec, burst=burst)
        self._client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)

    async def __aenter__(self) -> "ResilientHttpClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Close internal httpx client sessions cleanly."""
        await self._client.aclose()

    def _prepare_headers(
        self,
        headers: dict[str, str] | None,
        etag: str | None,
        last_modified: str | None,
    ) -> dict[str, str]:
        """Merge default user agent and conditional cache headers."""
        req_headers = {"User-Agent": DEFAULT_USER_AGENT}
        if headers:
            req_headers.update(headers)
        if etag:
            req_headers["If-None-Match"] = etag
        if last_modified:
            req_headers["If-Modified-Since"] = last_modified
        return req_headers

    def _calculate_backoff(self, attempt: int) -> float:
        """Compute exponential backoff with random jitter."""
        delay = min(10.0, self.base_backoff * (2**attempt))
        return delay + random.uniform(0, self.jitter)

    async def _send_with_retry(
        self,
        url: str,
        params: Mapping[str, HttpQueryParamValue] | None,
        headers: dict[str, str],
    ) -> httpx.Response:
        """Send GET request with retry backoff against transient network errors."""
        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = await self._client.get(url, params=params, headers=headers)
                if resp.status_code in {429, 502, 503, 504} and attempt < self.max_retries:
                    retry_after = resp.headers.get("retry-after")
                    wait_time = float(retry_after) if retry_after and retry_after.isdigit() else self._calculate_backoff(attempt)
                    await asyncio.sleep(wait_time)
                    continue
                return resp
            except (httpx.TransportError, httpx.TimeoutException) as err:
                last_err = err
                if attempt >= self.max_retries:
                    break
                await asyncio.sleep(self._calculate_backoff(attempt))
        raise HttpFetchError(f"HTTP request to '{url}' failed after retries: {last_err}") from last_err

    async def get(
        self,
        url: str,
        etag: str | None = None,
        last_modified: str | None = None,
        params: Mapping[str, HttpQueryParamValue] | None = None,
        headers: dict[str, str] | None = None,
        max_redirects: int = 3,
    ) -> HttpResponseResult:
        """Execute safe, rate-limited HTTP GET request with conditional caching and safe redirect following."""
        current_url = url
        current_params = params
        current_etag = etag
        current_last_modified = last_modified

        for redirect_hop in range(max_redirects + 1):
            validated_url = await self.ssrf_validator.validate_url(current_url)
            host = urlparse(validated_url).hostname or ""
            await self.rate_limiter.acquire(host)

            req_headers = self._prepare_headers(headers, current_etag, current_last_modified)
            resp = await self._send_with_retry(validated_url, current_params, req_headers)

            if resp.status_code == 304:
                return HttpResponseResult(
                    status_code=304,
                    not_modified=True,
                    text="",
                    etag=resp.headers.get("etag") or current_etag,
                    last_modified=resp.headers.get("last-modified") or current_last_modified,
                    headers=dict(resp.headers),
                )

            # Handle safe redirects (301, 302, 307, 308)
            if resp.status_code in {301, 302, 307, 308}:
                location = resp.headers.get("location")
                if not location:
                    raise HttpFetchError(f"Redirect status {resp.status_code} received without Location header for '{current_url}'")

                redirect_target = str(httpx.URL(validated_url).join(location))
                logger.info(
                    "Following safe redirect %d/%d from '%s' to '%s'",
                    redirect_hop + 1,
                    max_redirects,
                    current_url,
                    redirect_target,
                )
                if redirect_hop >= max_redirects:
                    raise HttpFetchError(f"Too many redirects (exceeded maximum of {max_redirects}) for '{url}'")

                current_url = redirect_target
                # Drop params, etag, and last_modified on cross-redirect request
                current_params = None
                current_etag = None
                current_last_modified = None
                continue

            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as err:
                raise HttpFetchError(
                    f"HTTP {err.response.status_code} error for '{current_url}': {err}"
                ) from err

            return HttpResponseResult(
                status_code=resp.status_code,
                not_modified=False,
                text=resp.text,
                etag=resp.headers.get("etag"),
                last_modified=resp.headers.get("last-modified"),
                headers=dict(resp.headers),
            )

        raise HttpFetchError(f"Too many redirects (exceeded maximum of {max_redirects}) for '{url}'")
