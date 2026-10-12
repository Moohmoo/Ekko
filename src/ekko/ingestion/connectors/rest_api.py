"""Universal REST API connector projecting JSON payloads into raw signals."""

from datetime import datetime, timezone
import json
from typing import Any

from ekko.config.schemas import SourceConfig
from ekko.ingestion.client import ResilientHttpClient
from ekko.ingestion.connectors.base import BaseConnector, compute_signal_id
from ekko.core.models import RawSignal, SignalStatus, SourceState
from ekko.logger import get_logger

logger = get_logger("ekko.ingestion.connectors.rest_api")


def _extract_items(data: Any, json_path: str | None) -> list[dict[str, Any]]:
    """Extract list of dictionary items from JSON tree based on path."""
    if not json_path:
        return data if isinstance(data, list) else []

    current = data
    for key in json_path.split("."):
        if isinstance(current, dict):
            current = current.get(key, [])
        else:
            return []
    return current if isinstance(current, list) else []


def _project_item(item: dict[str, Any], source_id: str) -> RawSignal:
    """Project a single dictionary hit into a normalized RawSignal model."""
    ext_id = str(item.get("objectID") or item.get("id") or "")
    title = str(item.get("title") or item.get("name") or "Untitled")
    url = str(item.get("url") or "")
    author = str(item.get("author") or item.get("by") or "") or None

    # Extract editorial content from standard text fields without dumping raw JSON dictionary
    candidate_text = (
        item.get("story_text")
        or item.get("comment_text")
        or item.get("body")
        or item.get("description")
        or ""
    )
    content = str(candidate_text).strip() if isinstance(candidate_text, str) else ""

    # Compute deterministic signal ID using external ID/URL, title, and content
    sig_id = compute_signal_id(url=url or ext_id, title=title, content=content or title)

    return RawSignal(
        id=sig_id,
        source_id=source_id,
        external_id=ext_id or None,
        url=url or None,
        title=title,
        raw_content=content,
        clean_content=content,
        author=author,
        status=SignalStatus.RETAINED,
    )


class RestApiConnector(BaseConnector):
    """Connector polling REST APIs with JSON projection and polite caching."""

    def __init__(self, http_client: ResilientHttpClient | None = None) -> None:
        self.http_client = http_client or ResilientHttpClient()

    async def fetch_signals(
        self,
        source: SourceConfig,
        state: SourceState | None = None,
    ) -> tuple[list[RawSignal], SourceState]:
        """Fetch REST API endpoint and map returned items to raw signals."""
        if not source.url:
            raise ValueError(f"Source '{source.id}' missing required URL")

        etag = state.etag if state else None
        last_modified = state.last_modified if state else None
        resp = await self.http_client.get(
            source.url,
            etag=etag,
            last_modified=last_modified,
            params=source.params,
            headers=source.headers,
        )

        now = datetime.now(timezone.utc)
        current_state = state or SourceState(
            id=source.id,
            source_type="rest_api",
            url_or_path=source.url,
        )
        current_state.last_polled_at = now

        if resp.not_modified:
            current_state.consecutive_errors = 0
            return [], current_state

        try:
            data = json.loads(resp.text)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse JSON response from source '%s': %s", source.id, exc)
            current_state.consecutive_errors += 1
            return [], current_state

        items = _extract_items(data, source.json_items_path)
        signals = [_project_item(item, source.id) for item in items[: source.max_items]]

        current_state.etag = resp.etag
        current_state.last_modified = resp.last_modified
        current_state.consecutive_errors = 0
        return signals, current_state
