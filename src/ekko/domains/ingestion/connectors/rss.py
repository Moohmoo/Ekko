"""Universal RSS and Atom XML connector with polite conditional polling."""

from datetime import datetime, timezone
import xml.etree.ElementTree as ET

from ekko.core.logger import get_logger
from ekko.domains.ingestion.client import ResilientHttpClient
from ekko.domains.ingestion.connectors.base import BaseConnector, compute_signal_id
from ekko.domains.radar.entities import RawSignal, SignalStatus, SourceState
from ekko.domains.system.contracts import SourceConfig

logger = get_logger("domains.ingestion.connectors.rss")

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _get_node(parent: ET.Element, path: str, ns: dict[str, str] | None = None) -> ET.Element | None:
    """Find child element handling namespace fallback safely without truthiness coercion."""
    if ns:
        found = parent.find(path, ns)
        if found is not None:
            return found
    clean_path = path.split(":")[-1] if ":" in path else path
    return parent.find(clean_path)


def _get_text(parent: ET.Element, path: str, ns: dict[str, str] | None = None) -> str:
    """Extract cleaned text from node safely."""
    node = _get_node(parent, path, ns)
    if node is not None and node.text:
        return " ".join(node.text.split())
    return ""


def _parse_atom_entries(root: ET.Element, source_id: str, max_items: int) -> list[RawSignal]:
    """Parse Atom XML feed entries into normalized RawSignal models."""
    entries = root.findall("atom:entry", ATOM_NS)
    if not entries:
        entries = root.findall("entry")

    signals: list[RawSignal] = []
    for entry in entries[:max_items]:
        title = _get_text(entry, "atom:title", ATOM_NS) or "Untitled"
        ext_id = _get_text(entry, "atom:id", ATOM_NS)
        summary = _get_text(entry, "atom:summary", ATOM_NS)
        author = _get_text(entry, "atom:author/atom:name", ATOM_NS) or None

        link_node = _get_node(entry, "atom:link", ATOM_NS)
        url = link_node.get("href") if link_node is not None else ext_id

        sig_id = compute_signal_id(url=url or ext_id, title=title, content=summary)
        signals.append(
            RawSignal(
                id=sig_id,
                source_id=source_id,
                external_id=ext_id or None,
                url=url or None,
                title=title,
                raw_content=summary,
                clean_content=summary,
                author=author,
                status=SignalStatus.RETAINED,
            )
        )
    return signals


def _parse_rss2_items(root: ET.Element, source_id: str, max_items: int) -> list[RawSignal]:
    """Parse RSS 2.0 XML channel items into normalized RawSignal models."""
    channel = root.find("channel")
    items = channel.findall("item") if channel is not None else root.findall("item")

    signals: list[RawSignal] = []
    for item in items[:max_items]:
        title = _get_text(item, "title") or "Untitled"
        ext_id = _get_text(item, "guid")
        url = _get_text(item, "link") or ext_id
        summary = _get_text(item, "description")
        author = _get_text(item, "author") or None

        sig_id = compute_signal_id(url=url or ext_id, title=title, content=summary)
        signals.append(
            RawSignal(
                id=sig_id,
                source_id=source_id,
                external_id=ext_id or None,
                url=url or None,
                title=title,
                raw_content=summary,
                clean_content=summary,
                author=author,
                status=SignalStatus.RETAINED,
            )
        )
    return signals


class RssConnector(BaseConnector):
    """Connector ingesting RSS 2.0 and Atom XML feeds with polite conditional caching."""

    def __init__(self, http_client: ResilientHttpClient | None = None) -> None:
        self.http_client = http_client or ResilientHttpClient()

    async def fetch_signals(
        self,
        source: SourceConfig,
        state: SourceState | None = None,
    ) -> tuple[list[RawSignal], SourceState]:
        """Fetch RSS/Atom feed and project items into raw signals."""
        if not source.url:
            raise ValueError(f"Source '{source.id}' missing required URL")

        etag = state.etag if state else None
        last_modified = state.last_modified if state else None
        resp = await self.http_client.get(
            source.url,
            etag=etag,
            last_modified=last_modified,
            headers=source.headers,
        )

        now = datetime.now(timezone.utc)
        current_state = state or SourceState(
            id=source.id,
            source_type="rss",
            url_or_path=source.url,
        )
        current_state.last_polled_at = now

        if resp.not_modified:
            current_state.consecutive_errors = 0
            return [], current_state

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as exc:
            logger.error("Failed to parse XML feed from source '%s': %s", source.id, exc)
            current_state.consecutive_errors += 1
            return [], current_state

        tag = root.tag.lower()
        if "feed" in tag:
            signals = _parse_atom_entries(root, source.id, source.max_items)
        else:
            signals = _parse_rss2_items(root, source.id, source.max_items)

        current_state.etag = resp.etag
        current_state.last_modified = resp.last_modified
        current_state.consecutive_errors = 0
        return signals, current_state
