"""Unit tests for SignalWatchTool and HN Algolia signal gathering."""

import pytest
from pydantic import ValidationError

from ekko.core.ports import ToolPort
from ekko.tools.signal_watch import SignalWatchInput, SignalWatchTool


def test_signal_watch_implements_tool_port() -> None:
    """Ensure SignalWatchTool complies with domain ToolPort protocol."""
    tool = SignalWatchTool()
    assert isinstance(tool, ToolPort)
    assert tool.name == "signal_watch"
    assert "signal" in tool.description.lower() or "hacker news" in tool.description.lower()


def test_signal_watch_input_defaults() -> None:
    """Ensure default parameters adhere to agreed specifications."""
    schema = SignalWatchInput()
    assert schema.query is None
    assert schema.days == 7
    assert schema.min_score == 50
    assert schema.limit == 10


def test_signal_watch_input_validation_bounds() -> None:
    """Ensure validation enforces strict bounds on days and limit."""
    # days must be between 1 and 30
    with pytest.raises(ValidationError):
        SignalWatchInput(days=0)
    with pytest.raises(ValidationError):
        SignalWatchInput(days=31)

    # limit must be between 1 and 20
    with pytest.raises(ValidationError):
        SignalWatchInput(limit=0)
    with pytest.raises(ValidationError):
        SignalWatchInput(limit=21)

    # min_score must be non-negative
    with pytest.raises(ValidationError):
        SignalWatchInput(min_score=-1)


def test_signal_watch_json_schema() -> None:
    """Ensure generated JSON schema correctly exposes parameters to LLM."""
    tool = SignalWatchTool()
    schema = tool.get_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "signal_watch"
    parameters = schema["function"]["parameters"]
    assert parameters["type"] == "object"
    props = parameters["properties"]
    assert "query" in props
    assert "days" in props
    assert "min_score" in props
    assert "limit" in props


@pytest.mark.asyncio
async def test_signal_watch_query_params_defaults() -> None:
    """Ensure default parameters construct correct Algolia query with tags and timestamp."""
    import time
    from unittest.mock import AsyncMock, patch
    import httpx

    tool = SignalWatchTool()
    now = int(time.time())
    mock_resp = httpx.Response(
        200,
        json={"hits": []},
        request=httpx.Request("GET", "https://hn.algolia.com/api/v1/search_by_date"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        result = await tool.execute()

    assert result.success is True
    mock_get.assert_awaited_once()
    called_url = mock_get.call_args[0][0]
    called_kwargs = mock_get.call_args[1]

    assert called_url == "https://hn.algolia.com/api/v1/search_by_date"
    params = called_kwargs["params"]
    assert params["tags"] == "story"
    assert params["hitsPerPage"] == 10
    assert "query" not in params

    filters = params["numericFilters"]
    assert "points>=50" in filters
    expected_cutoff = now - (7 * 86400)
    for item in filters.split(","):
        if item.startswith("created_at_i>="):
            ts = int(item.split(">=")[1])
            assert abs(ts - expected_cutoff) <= 2


@pytest.mark.asyncio
async def test_signal_watch_query_params_custom() -> None:
    """Ensure custom query, days, min_score and limit are forwarded properly."""
    import time
    from unittest.mock import AsyncMock, patch
    import httpx

    tool = SignalWatchTool()
    now = int(time.time())
    mock_resp = httpx.Response(
        200,
        json={"hits": []},
        request=httpx.Request("GET", "https://hn.algolia.com/api/v1/search_by_date"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        result = await tool.execute(query="quantum", days=3, min_score=100, limit=5)

    assert result.success is True
    mock_get.assert_awaited_once()
    called_kwargs = mock_get.call_args[1]
    params = called_kwargs["params"]

    assert params["query"] == "quantum"
    assert params["hitsPerPage"] == 5
    assert "points>=100" in params["numericFilters"]
    expected_cutoff = now - (3 * 86400)
    for item in params["numericFilters"].split(","):
        if item.startswith("created_at_i>="):
            ts = int(item.split(">=")[1])
            assert abs(ts - expected_cutoff) <= 2


@pytest.mark.asyncio
async def test_signal_watch_compact_output_with_url_fallback() -> None:
    """Ensure raw Algolia hits are projected compactly with fallback URL for Ask/Show HN."""
    import json
    from unittest.mock import AsyncMock, patch
    import httpx

    tool = SignalWatchTool()
    sample_hits = [
        {
            "title": "Show HN: Local WebGPU Inference Engine",
            "url": "https://github.com/engine/webgpu",
            "points": 342,
            "num_comments": 128,
            "created_at": "2026-10-08T12:00:00Z",
            "objectID": "123456",
        },
        {
            "title": "Ask HN: What is your local AI stack in 2026?",
            "url": None,
            "points": 95,
            "num_comments": 40,
            "created_at": "2026-10-09T08:00:00Z",
            "objectID": "789012",
        },
    ]

    mock_resp = httpx.Response(
        200,
        json={"hits": sample_hits},
        request=httpx.Request("GET", "https://hn.algolia.com/api/v1/search_by_date"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        result = await tool.execute()

    assert result.success is True
    items = json.loads(result.content)
    assert len(items) == 2

    # Verify first item projection
    assert items[0]["title"] == "Show HN: Local WebGPU Inference Engine"
    assert items[0]["url"] == "https://github.com/engine/webgpu"
    assert items[0]["points"] == 342
    assert items[0]["comments"] == 128
    assert items[0]["date"] == "2026-10-08T12:00:00Z"

    # Verify second item with url fallback
    assert items[1]["title"] == "Ask HN: What is your local AI stack in 2026?"
    assert items[1]["url"] == "https://news.ycombinator.com/item?id=789012"
    assert items[1]["points"] == 95
    assert items[1]["comments"] == 40


@pytest.mark.asyncio
async def test_signal_watch_empty_hits() -> None:
    """Ensure empty hits list returns clean message without error."""
    from unittest.mock import AsyncMock, patch
    import httpx

    tool = SignalWatchTool()
    mock_resp = httpx.Response(
        200,
        json={"hits": []},
        request=httpx.Request("GET", "https://hn.algolia.com/api/v1/search_by_date"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        result = await tool.execute()

    assert result.success is True
    assert "no signals found" in result.content.lower()


@pytest.mark.asyncio
async def test_signal_watch_network_error_resilience() -> None:
    """Ensure network failure returns graceful ToolResult with error detail."""
    from unittest.mock import AsyncMock, patch
    import httpx

    tool = SignalWatchTool()

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectTimeout("Connection timed out")
        result = await tool.execute()

    assert result.success is False
    assert result.error == "ConnectTimeout"
    assert "connection timed out" in result.content.lower()


