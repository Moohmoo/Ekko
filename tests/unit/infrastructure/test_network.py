"""Unit tests for resilient HTTP client with SSRF protection, token bucket, and conditional cache."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from ekko.infrastructure.network.client import HttpResponseResult, ResilientHttpClient
from ekko.infrastructure.network.rate_limiter import DomainRateLimiter
from ekko.infrastructure.network.ssrf import SSRFValidator, SSRFViolationError


def test_ssrf_validator_blocks_private_and_loopback_ips() -> None:
    """Ensure SSRF validator forbids loopback, RFC 1918, link-local, and cloud metadata."""
    validator = SSRFValidator()

    # Blocked IPs
    assert validator.is_ip_safe("127.0.0.1") is False
    assert validator.is_ip_safe("127.0.1.1") is False
    assert validator.is_ip_safe("10.0.0.1") is False
    assert validator.is_ip_safe("172.16.0.1") is False
    assert validator.is_ip_safe("192.168.1.1") is False
    assert validator.is_ip_safe("169.254.169.254") is False
    assert validator.is_ip_safe("0.0.0.0") is False
    assert validator.is_ip_safe("::1") is False
    assert validator.is_ip_safe("fe80::1") is False
    assert validator.is_ip_safe("fc00::1") is False

    # Allowed public IPs
    assert validator.is_ip_safe("8.8.8.8") is True
    assert validator.is_ip_safe("1.1.1.1") is True
    assert validator.is_ip_safe("142.250.190.46") is True


def test_ssrf_validator_url_validation() -> None:
    """Ensure validate_url rejects invalid schemes and resolved private addresses."""
    validator = SSRFValidator()

    with pytest.raises(SSRFViolationError, match="Scheme"):
        validator.validate_url("file:///etc/passwd")

    with pytest.raises(SSRFViolationError, match="Forbidden IP"):
        validator.validate_url("http://127.0.0.1:8080/metrics")

    with pytest.raises(SSRFViolationError, match="Forbidden IP"):
        validator.validate_url("http://169.254.169.254/latest/meta-data/")

    # Mock DNS resolution for hostnames
    with patch("socket.getaddrinfo") as mock_getaddrinfo:
        # Simulate local.test resolving to 192.168.1.50
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("192.168.1.50", 80))
        ]
        with pytest.raises(SSRFViolationError, match="Forbidden resolved IP"):
            validator.validate_url("https://local.test/secret")

        # Simulate api.public.com resolving to 93.184.216.34
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 443))
        ]
        safe_url = validator.validate_url("https://api.public.com/data")
        assert safe_url == "https://api.public.com/data"


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter() -> None:
    """Ensure token bucket limits frequency per host without blocking different hosts."""
    limiter = DomainRateLimiter(rate_per_sec=10.0, burst=2)

    # First 2 requests should be instant (burst capacity)
    await limiter.acquire("api.example.com")
    await limiter.acquire("api.example.com")

    # Another host should have its own separate bucket
    await limiter.acquire("other.example.com")


@pytest.mark.asyncio
async def test_resilient_http_client_handles_304_not_modified() -> None:
    """Ensure client passes conditional headers and returns not_modified=True on 304."""
    client = ResilientHttpClient()

    mock_resp = httpx.Response(
        status_code=304,
        headers={"ETag": '"abc123etag"'},
        request=httpx.Request("GET", "https://api.example.com/feed"),
    )

    with patch.object(client.ssrf_validator, "validate_url", return_value="https://api.example.com/feed"):
        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            result: HttpResponseResult = await client.get(
                "https://api.example.com/feed",
                etag='"abc123etag"',
                last_modified="Tue, 15 Nov 1994 12:45:26 GMT",
            )

            assert result.status_code == 304
            assert result.not_modified is True
            assert result.text == ""
            assert result.etag == '"abc123etag"'

            _, kwargs = mock_get.call_args
            headers = kwargs["headers"]
            assert headers["If-None-Match"] == '"abc123etag"'
            assert headers["If-Modified-Since"] == "Tue, 15 Nov 1994 12:45:26 GMT"

    await client.close()


@pytest.mark.asyncio
async def test_resilient_http_client_extracts_etag_on_200() -> None:
    """Ensure client captures response ETag and Last-Modified on 200 OK."""
    client = ResilientHttpClient()

    mock_resp = httpx.Response(
        status_code=200,
        text="<xml>Fresh Content</xml>",
        headers={
            "ETag": '"new_etag_999"',
            "Last-Modified": "Fri, 10 Oct 2026 12:00:00 GMT",
        },
        request=httpx.Request("GET", "https://api.example.com/feed"),
    )

    with patch.object(client.ssrf_validator, "validate_url", return_value="https://api.example.com/feed"):
        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            result = await client.get("https://api.example.com/feed")

            assert result.status_code == 200
            assert result.not_modified is False
            assert result.text == "<xml>Fresh Content</xml>"
            assert result.etag == '"new_etag_999"'
            assert result.last_modified == "Fri, 10 Oct 2026 12:00:00 GMT"

    await client.close()


@pytest.mark.asyncio
async def test_resilient_http_client_retries_with_backoff_on_transient_failure() -> None:
    """Ensure client retries transient transport errors before succeeding."""
    client = ResilientHttpClient(max_retries=2, base_backoff=0.01, jitter=0.01)

    success_resp = httpx.Response(
        status_code=200,
        text="Recovered data",
        request=httpx.Request("GET", "https://api.example.com/flaky"),
    )

    with patch.object(client.ssrf_validator, "validate_url", return_value="https://api.example.com/flaky"):
        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                httpx.ConnectTimeout("Connection timed out"),
                success_resp,
            ]
            result = await client.get("https://api.example.com/flaky")
            assert result.status_code == 200
            assert result.text == "Recovered data"
            assert mock_get.call_count == 2

    await client.close()


@pytest.mark.asyncio
async def test_resilient_http_client_blocks_ssrf_before_request() -> None:
    """Ensure client aborts without emitting HTTP call when SSRF is detected."""
    client = ResilientHttpClient()

    with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
        with pytest.raises(SSRFViolationError):
            await client.get("http://127.0.0.1:9000/private")
        mock_get.assert_not_called()

    await client.close()
