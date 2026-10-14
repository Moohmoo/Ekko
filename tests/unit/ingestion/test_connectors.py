"""Unit tests for universal ingestion connectors (RSS/Atom and REST API)."""

from unittest.mock import AsyncMock
import pytest

from ekko.domains.ingestion.client import HttpResponseResult
from ekko.domains.ingestion.connectors.rest_api import RestApiConnector
from ekko.domains.ingestion.connectors.rss import RssConnector
from ekko.domains.radar.entities import SignalStatus, SourceState
from ekko.domains.system.contracts import SourceConfig

SAMPLE_ATOM_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>arXiv cs.AI</title>
  <entry>
    <id>http://arxiv.org/abs/2610.12345v1</id>
    <title>Deep Reasoning in Small Models</title>
    <summary>A study on distillation into 1B architectures.</summary>
    <published>2026-10-09T12:00:00Z</published>
    <author><name>Jane Doe</name></author>
    <link href="http://arxiv.org/abs/2610.12345v1"/>
  </entry>
</feed>
"""

SAMPLE_RSS2_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>Tech News</title>
  <link>https://technews.example.com</link>
  <item>
    <guid>tech-news-item-1</guid>
    <title>Quantum Computing Milestone</title>
    <link>https://technews.example.com/quantum</link>
    <description>Fault-tolerant qubits demonstrated.</description>
    <pubDate>Fri, 10 Oct 2026 09:30:00 GMT</pubDate>
    <author>editor@example.com</author>
  </item>
</channel>
</rss>
"""

SAMPLE_REST_JSON = """{
  "hits": [
    {
      "objectID": "40001",
      "title": "Open Source Foundation Model Release",
      "url": "https://example.com/os-model",
      "points": 340,
      "num_comments": 120,
      "author": "dev_guru",
      "created_at": "2026-10-10T08:00:00Z"
    }
  ]
}"""


@pytest.mark.asyncio
async def test_rss_connector_parses_atom_feed() -> None:
    """Ensure RssConnector parses Atom XML feeds into normalized RawSignals."""
    mock_http = AsyncMock()
    mock_http.get.return_value = HttpResponseResult(
        status_code=200,
        not_modified=False,
        text=SAMPLE_ATOM_XML,
        etag='"atom_etag"',
        last_modified="Fri, 10 Oct 2026 12:00:00 GMT",
    )

    connector = RssConnector(http_client=mock_http)
    source = SourceConfig(id="arxiv_ai", type="rss", url="https://export.arxiv.org/api/query")

    signals, new_state = await connector.fetch_signals(source)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.source_id == "arxiv_ai"
    assert sig.title == "Deep Reasoning in Small Models"
    assert "1B architectures" in (sig.clean_content or "")
    assert sig.author == "Jane Doe"
    assert sig.status == SignalStatus.RETAINED

    assert new_state.id == "arxiv_ai"
    assert new_state.etag == '"atom_etag"'
    assert new_state.consecutive_errors == 0


@pytest.mark.asyncio
async def test_rss_connector_parses_rss2_feed() -> None:
    """Ensure RssConnector parses RSS 2.0 XML feeds into normalized RawSignals."""
    mock_http = AsyncMock()
    mock_http.get.return_value = HttpResponseResult(
        status_code=200,
        not_modified=False,
        text=SAMPLE_RSS2_XML,
        etag='"rss_etag"',
    )

    connector = RssConnector(http_client=mock_http)
    source = SourceConfig(id="tech_rss", type="rss", url="https://technews.example.com/rss")

    signals, new_state = await connector.fetch_signals(source)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.source_id == "tech_rss"
    assert sig.title == "Quantum Computing Milestone"
    assert sig.url == "https://technews.example.com/quantum"
    assert sig.author == "editor@example.com"
    assert new_state.etag == '"rss_etag"'


@pytest.mark.asyncio
async def test_rss_connector_handles_304_not_modified() -> None:
    """Ensure RssConnector yields empty signals on 304 Not Modified without error."""
    mock_http = AsyncMock()
    mock_http.get.return_value = HttpResponseResult(
        status_code=304,
        not_modified=True,
        text="",
        etag='"cached_etag"',
    )

    connector = RssConnector(http_client=mock_http)
    source = SourceConfig(id="feed_cached", type="rss", url="https://example.com/rss")
    state = SourceState(id="feed_cached", source_type="rss", url_or_path="https://example.com/rss", etag='"cached_etag"')

    signals, updated_state = await connector.fetch_signals(source, state=state)

    assert len(signals) == 0
    assert updated_state.etag == '"cached_etag"'


@pytest.mark.asyncio
async def test_rest_api_connector_parses_json_hits() -> None:
    """Ensure RestApiConnector navigates json_items_path and projects hits."""
    mock_http = AsyncMock()
    mock_http.get.return_value = HttpResponseResult(
        status_code=200,
        not_modified=False,
        text=SAMPLE_REST_JSON,
        etag='"api_etag"',
    )

    connector = RestApiConnector(http_client=mock_http)
    source = SourceConfig(
        id="hn_signals",
        type="rest_api",
        url="https://hn.algolia.com/api/v1/search",
        json_items_path="hits",
    )

    signals, new_state = await connector.fetch_signals(source)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.source_id == "hn_signals"
    assert sig.external_id == "40001"
    assert sig.title == "Open Source Foundation Model Release"
    assert sig.url == "https://example.com/os-model"
    assert sig.author == "dev_guru"
    assert sig.clean_content == ""
    assert sig.raw_content == ""
    assert new_state.etag == '"api_etag"'


@pytest.mark.asyncio
async def test_rest_api_connector_extracts_story_text_and_never_leaks_raw_json() -> None:
    """Ensure editorial story_text is extracted cleanly while raw JSON dictionary is never dumped."""
    json_with_metadata = """{
      "hits": [
        {
          "objectID": "55555",
          "title": "Show HN: Local AI Project",
          "url": "https://news.ycombinator.com/item?id=55555",
          "story_text": "We built a new local agentic PKM system with SQLite.",
          "_highlightResult": {"title": {"value": "Show HN..."}},
          "_tags": ["story", "author_dev"]
        }
      ]
    }"""
    mock_http = AsyncMock()
    mock_http.get.return_value = HttpResponseResult(
        status_code=200,
        not_modified=False,
        text=json_with_metadata,
        etag='"api_etag"',
    )

    connector = RestApiConnector(http_client=mock_http)
    source = SourceConfig(
        id="hn_signals",
        type="rest_api",
        url="https://hn.algolia.com/api/v1/search",
        json_items_path="hits",
    )

    signals, _ = await connector.fetch_signals(source)
    assert len(signals) == 1
    sig = signals[0]
    assert sig.clean_content == "We built a new local agentic PKM system with SQLite."
    assert "_highlightResult" not in sig.clean_content
    assert not sig.clean_content.startswith("{")


@pytest.mark.asyncio
async def test_rest_api_connector_handles_304_not_modified() -> None:
    """Ensure RestApiConnector yields empty list on 304 without error."""
    mock_http = AsyncMock()
    mock_http.get.return_value = HttpResponseResult(
        status_code=304,
        not_modified=True,
        text="",
        etag='"cached_api_etag"',
    )

    connector = RestApiConnector(http_client=mock_http)
    source = SourceConfig(id="api_cached", type="rest_api", url="https://api.test/data")
    state = SourceState(id="api_cached", source_type="rest_api", url_or_path="https://api.test/data", etag='"cached_api_etag"')

    signals, updated_state = await connector.fetch_signals(source, state=state)

    assert len(signals) == 0
    assert updated_state.etag == '"cached_api_etag"'


@pytest.mark.asyncio
async def test_rest_api_connector_handles_malformed_json() -> None:
    """Ensure RestApiConnector handles malformed JSON without raising and increments consecutive_errors."""
    mock_http = AsyncMock()
    mock_http.get.return_value = HttpResponseResult(
        status_code=200,
        not_modified=False,
        text="<html><body>Not JSON</body></html>",
    )

    connector = RestApiConnector(http_client=mock_http)
    source = SourceConfig(id="api_bad", type="rest_api", url="https://api.test/bad")

    signals, updated_state = await connector.fetch_signals(source)

    assert len(signals) == 0
    assert updated_state.consecutive_errors == 1


@pytest.mark.asyncio
async def test_rss_connector_handles_malformed_xml() -> None:
    """Ensure RssConnector handles malformed XML without raising and increments consecutive_errors."""
    mock_http = AsyncMock()
    mock_http.get.return_value = HttpResponseResult(
        status_code=200,
        not_modified=False,
        text="<feed><unclosed_tag>",
    )

    connector = RssConnector(http_client=mock_http)
    source = SourceConfig(id="rss_bad", type="rss", url="https://rss.test/bad")

    signals, updated_state = await connector.fetch_signals(source)

    assert len(signals) == 0
    assert updated_state.consecutive_errors == 1


def test_url_normalization_strips_tracking() -> None:
    """Ensure normalize_url strips query tracking params and standardizes url."""
    from ekko.domains.ingestion.connectors.base import normalize_url

    raw = "https://EXAMPLE.COM/articles/test/?utm_source=twitter&utm_medium=social&ref=hn#section"
    normalized = normalize_url(raw)
    assert normalized == "https://example.com/articles/test"


def test_cross_source_deduplication_same_signal_id() -> None:
    """Ensure compute_signal_id generates identical id across sources and tracking params."""
    from ekko.domains.ingestion.connectors.base import compute_signal_id

    url1 = "https://example.com/post?utm_source=reddit"
    url2 = "https://example.com/post?ref=newsletter"

    id1 = compute_signal_id(url=url1, title="Breaking News")
    id2 = compute_signal_id(url=url2, title="Breaking News")

    assert id1 == id2
    assert id1.startswith("sig_")

