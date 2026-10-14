"""Strict SSRF validation guarding against local and private network probing."""

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

from ekko.core.errors import EkkoError


class SSRFViolationError(EkkoError):
    """Exception raised when a URL targets a private, loopback, or cloud-metadata IP."""


class SSRFValidator:
    """Validates URLs and resolved IP addresses against SSRF attacks."""

    ALLOWED_SCHEMES = {"http", "https"}

    def is_ip_safe(self, ip_str: str) -> bool:
        """Verify whether an IP address is a safe public address."""
        try:
            ip = ipaddress.ip_address(ip_str.strip())
        except ValueError:
            return False

        return not (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )

    async def _resolve_host_ips(self, host: str) -> list[str]:
        """Resolve host name to IP addresses asynchronously using system DNS without blocking loop."""
        loop = asyncio.get_running_loop()
        try:
            addr_info = await loop.getaddrinfo(host, None)
            return [str(sockaddr[0]) for _, _, _, _, sockaddr in addr_info]
        except socket.gaierror as exc:
            raise SSRFViolationError(f"DNS resolution failure for host '{host}': {exc}") from exc

    async def validate_url(self, url: str) -> str:
        """Validate URL scheme and ensure resolved target IPs are public (non-blocking)."""
        parsed = urlparse(url.strip())
        if parsed.scheme.lower() not in self.ALLOWED_SCHEMES:
            raise SSRFViolationError(
                f"Scheme '{parsed.scheme}' not allowed. Must be http or https."
            )

        host = parsed.hostname
        if not host:
            raise SSRFViolationError(f"Missing host in URL: '{url}'")

        try:
            ip = ipaddress.ip_address(host)
            if not self.is_ip_safe(str(ip)):
                raise SSRFViolationError(f"Forbidden IP address in URL: '{host}'")
            return url
        except ValueError:
            pass

        resolved_ips = await self._resolve_host_ips(host)
        if not resolved_ips:
            raise SSRFViolationError(f"No IP addresses resolved for host '{host}'")

        for ip_candidate in resolved_ips:
            if not self.is_ip_safe(ip_candidate):
                raise SSRFViolationError(
                    f"Forbidden resolved IP address '{ip_candidate}' for host '{host}'"
                )

        return url
