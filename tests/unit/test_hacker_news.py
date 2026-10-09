"""Unit tests for HackerNewsTool and HN Algolia consensus signal gathering."""

import json
import time
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from pydantic import ValidationError

from ekko.core.ports import ToolPort
from ekko.tools.hacker_news import HackerNewsInput, HackerNewsTool


def test_hacker_news_implements_tool_port() -> None:
    """Ensure HackerNewsTool complies with domain ToolPort protocol."""
    tool = HackerNewsTool()
    assert isinstance(tool, ToolPort)
    assert tool.name == "hacker_news"
    assert "hacker news" in tool.description.lower()


def test_hacker_news_input_defaults() -> None:
    """Ensure default parameters adhere to agreed specifications."""
    schema = HackerNewsInput()
    assert not hasattr(schema, "query")
    assert schema.days == 7
    assert schema.min_score == 150
    assert schema.limit == 20


def test_hacker_news_input_validation_bounds() -> None:
    """Ensure validation enforces strict bounds on days, min_score and limit."""
    # days must be between 1 and 30
    with pytest.raises(ValidationError):
        HackerNewsInput(days=0)
    with pytest.raises(ValidationError):
        HackerNewsInput(days=31)

    # limit must be between 5 and 30
    with pytest.raises(ValidationError):
        HackerNewsInput(limit=4)
    with pytest.raises(ValidationError):
        HackerNewsInput(limit=31)

    # min_score must be at least 50
    with pytest.raises(ValidationError):
        HackerNewsInput(min_score=49)


def test_hacker_news_json_schema() -> None:
    """Ensure generated JSON schema exposes only radar parameters without query."""
    tool = HackerNewsTool()
    schema = tool.get_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "hacker_news"
    parameters = schema["function"]["parameters"]
    assert parameters["type"] == "object"
    props = parameters["properties"]
    assert "query" not in props
    assert "days" in props
    assert "min_score" in props
    assert "limit" in props


@pytest.mark.asyncio
async def test_hacker_news_query_params_defaults() -> None:
    """Ensure default parameters construct correct Algolia query with tags and timestamp."""
    tool = HackerNewsTool()
    now = int(time.time())
    mock_resp = httpx.Response(
        200,
        json={"hits": []},
        request=httpx.Request("GET", "https://hn.algolia.com/api/v1/search"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        result = await tool.execute()

    assert result.success is True
    mock_get.assert_awaited_once()
    called_url = mock_get.call_args[0][0]
    called_kwargs = mock_get.call_args[1]

    assert called_url == "https://hn.algolia.com/api/v1/search"
    params = called_kwargs["params"]
    assert params["tags"] == "story"
    assert params["hitsPerPage"] == 20
    assert "query" not in params

    filters = params["numericFilters"]
    assert "points>=150" in filters
    expected_cutoff = now - (7 * 86400)
    for item in filters.split(","):
        if item.startswith("created_at_i>="):
            ts = int(item.split(">=")[1])
            assert abs(ts - expected_cutoff) <= 2


@pytest.mark.asyncio
async def test_hacker_news_query_params_custom() -> None:
    """Ensure custom days, min_score and limit are forwarded properly."""
    tool = HackerNewsTool()
    now = int(time.time())
    mock_resp = httpx.Response(
        200,
        json={"hits": []},
        request=httpx.Request("GET", "https://hn.algolia.com/api/v1/search"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        result = await tool.execute(days=3, min_score=200, limit=10)

    assert result.success is True
    mock_get.assert_awaited_once()
    called_kwargs = mock_get.call_args[1]
    params = called_kwargs["params"]

    assert "query" not in params
    assert params["hitsPerPage"] == 10
    assert "points>=200" in params["numericFilters"]
    expected_cutoff = now - (3 * 86400)
    for item in params["numericFilters"].split(","):
        if item.startswith("created_at_i>="):
            ts = int(item.split(">=")[1])
            assert abs(ts - expected_cutoff) <= 2


@pytest.mark.asyncio
async def test_hacker_news_compact_output_with_url_fallback() -> None:
    """Ensure raw Algolia hits are projected compactly with fallback URL for Ask/Show HN."""
    tool = HackerNewsTool()
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
        request=httpx.Request("GET", "https://hn.algolia.com/api/v1/search"),
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
async def test_hacker_news_empty_hits() -> None:
    """Ensure empty hits list returns clean message without error."""
    tool = HackerNewsTool()
    mock_resp = httpx.Response(
        200,
        json={"hits": []},
        request=httpx.Request("GET", "https://hn.algolia.com/api/v1/search"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        result = await tool.execute()

    assert result.success is True
    assert "no signals found" in result.content.lower()


@pytest.mark.asyncio
async def test_hacker_news_network_error_resilience() -> None:
    """Ensure network failure returns graceful ToolResult with error detail."""
    tool = HackerNewsTool()

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectTimeout("Connection timed out")
        result = await tool.execute()

    assert result.success is False
    assert result.error == "ConnectTimeout"
    assert "connection timed out" in result.content.lower()
