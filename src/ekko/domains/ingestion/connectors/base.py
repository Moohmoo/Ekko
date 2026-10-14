"""Base abstraction for universal ingestion connectors and deduplication utilities."""

from abc import ABC, abstractmethod
import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ekko.domains.radar.entities import RawSignal, SourceState
from ekko.domains.system.contracts import SourceConfig

_TRACKING_PARAM_PREFIXES = ("utm_",)
_TRACKING_PARAM_EXACT = {
    "ref",
    "source",
    "fbclid",
    "gclid",
    "mc_eid",
    "mc_cid",
    "_hsenc",
    "_hsmi",
    "ncid",
}


def normalize_url(url: str) -> str:
    """Normalize URL by stripping tracking parameters, fragments, and standardizing host/scheme."""
    cleaned = url.strip()
    if not cleaned:
        return ""
    try:
        parsed = urlparse(cleaned)
        if not parsed.scheme or not parsed.netloc:
            return cleaned

        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        # Strip default HTTP/HTTPS ports
        if (scheme == "http" and netloc.endswith(":80")) or (scheme == "https" and netloc.endswith(":443")):
            netloc = netloc.rsplit(":", 1)[0]

        filtered_params: list[tuple[str, str]] = []
        for k, v in parse_qsl(parsed.query, keep_blank_values=False):
            k_lower = k.lower()
            if any(k_lower.startswith(prefix) for prefix in _TRACKING_PARAM_PREFIXES):
                continue
            if k_lower in _TRACKING_PARAM_EXACT:
                continue
            filtered_params.append((k, v))

        filtered_params.sort(key=lambda x: x[0])
        new_query = urlencode(filtered_params)

        path = parsed.path
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]

        return urlunparse((scheme, netloc, path, parsed.params, new_query, ""))
    except Exception:
        return cleaned


def compute_signal_id(url: str | None = None, title: str = "", content: str | None = None) -> str:
    """Compute deterministic cross-source signal ID without source_id coupling."""
    norm_url = normalize_url(url) if url else ""
    if norm_url:
        seed = f"url:{norm_url}"
    else:
        norm_title = re.sub(r"\s+", " ", title.strip().lower())
        norm_content = re.sub(r"\s+", " ", (content or "")[:300].strip().lower())
        seed = f"content:{norm_title}:{norm_content}"

    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"sig_{digest}"


class BaseConnector(ABC):
    """Abstract connector protocol driving raw signal extraction."""

    @abstractmethod
    async def fetch_signals(
        self,
        source: SourceConfig,
        state: SourceState | None = None,
    ) -> tuple[list[RawSignal], SourceState]:
        """Fetch fresh signals from source using polite polling and update state."""
