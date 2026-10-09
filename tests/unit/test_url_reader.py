"""Unit tests for UrlReaderTool contract and input validation."""

import pytest
from pydantic import ValidationError

from ekko.core.ports import ToolPort
from ekko.tools.url_reader import UrlReaderInput, UrlReaderTool


def test_url_reader_implements_tool_port() -> None:
    """Ensure UrlReaderTool satisfies ToolPort protocol."""
    tool = UrlReaderTool()
    assert isinstance(tool, ToolPort)
    assert tool.name == "url_reader"
    assert "url" in tool.description.lower() or "web" in tool.description.lower()


def test_url_reader_input_defaults() -> None:
    """Ensure valid URL is accepted and max_chars defaults to 12000."""
    schema = UrlReaderInput(url="https://example.com/article")  # type: ignore[arg-type]
    assert str(schema.url).rstrip("/") == "https://example.com/article"
    assert schema.max_chars == 12000


def test_url_reader_input_validation_bounds() -> None:
    """Ensure invalid URLs and out-of-bound max_chars are rejected."""
    # Missing url
    with pytest.raises(ValidationError):
        UrlReaderInput()  # type: ignore[call-arg]

    # Non-HTTP/HTTPS schemes
    with pytest.raises(ValidationError):
        UrlReaderInput(url="ftp://example.com/file")  # type: ignore[arg-type]

    # Invalid URL formatting
    with pytest.raises(ValidationError):
        UrlReaderInput(url="not_a_valid_url")  # type: ignore[arg-type]

    # max_chars bounds: [1000, 100000]
    with pytest.raises(ValidationError):
        UrlReaderInput(url="https://example.com", max_chars=999)  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        UrlReaderInput(url="https://example.com", max_chars=100001)  # type: ignore[arg-type]


def test_url_reader_json_schema() -> None:
    """Ensure generated schema exposes url (required) and max_chars."""
    tool = UrlReaderTool()
    schema = tool.get_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "url_reader"

    parameters = schema["function"]["parameters"]
    assert parameters["type"] == "object"
    props = parameters["properties"]
    assert "url" in props
    assert "max_chars" in props
    assert "url" in parameters["required"]


@pytest.mark.asyncio
async def test_url_reader_nominal_fetch_and_markdown_extraction() -> None:
    """Ensure HTTP client fetches URL with standard User-Agent and extracts Markdown."""
    from unittest.mock import AsyncMock, patch
    import httpx

    tool = UrlReaderTool()
    sample_html = "<html><body><article><h1>Quantum Leap</h1><p>Groundbreaking discovery in physics.</p></article></body></html>"
    expected_markdown = "# Quantum Leap\n\nGroundbreaking discovery in physics."

    mock_resp = httpx.Response(
        200,
        text=sample_html,
        request=httpx.Request("GET", "https://example.com/physics"),
    )

    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch("trafilatura.extract") as mock_extract,
    ):
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client_cls.return_value = mock_client

        mock_extract.return_value = expected_markdown

        result = await tool.execute(url="https://example.com/physics")

        # Verify client initialization arguments
        mock_client_cls.assert_called_once()
        client_kwargs = mock_client_cls.call_args[1]
        assert client_kwargs.get("follow_redirects") is True
        assert client_kwargs.get("timeout") == 10.0
        headers = client_kwargs.get("headers", {})
        assert "User-Agent" in headers
        assert "Mozilla" in headers["User-Agent"]

        # Verify request call
        mock_client.get.assert_awaited_once_with("https://example.com/physics")

        # Verify trafilatura arguments
        mock_extract.assert_called_once_with(
            sample_html,
            output_format="markdown",
            include_links=True,
        )

        assert result.success is True
        assert result.content == expected_markdown


@pytest.mark.asyncio
async def test_url_reader_truncates_when_exceeding_max_chars() -> None:
    """Ensure extracted content exceeding max_chars is cleanly truncated with notice."""
    from unittest.mock import AsyncMock, patch
    import httpx

    tool = UrlReaderTool()
    long_markdown = "A" * 5000
    mock_resp = httpx.Response(200, text="<html>...</html>", request=httpx.Request("GET", "https://example.com"))

    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch("trafilatura.extract", return_value=long_markdown),
    ):
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client_cls.return_value = mock_client

        result = await tool.execute(url="https://example.com", max_chars=2000)

    assert result.success is True
    assert result.content.startswith("A" * 2000)
    assert result.content.endswith("\n\n[... Contenu tronqué pour respecter la fenêtre de contexte ...]")
    assert len(result.content) == 2000 + len("\n\n[... Contenu tronqué pour respecter la fenêtre de contexte ...]")


@pytest.mark.asyncio
async def test_url_reader_does_not_truncate_when_within_max_chars() -> None:
    """Ensure short content is returned intact without truncation message."""
    from unittest.mock import AsyncMock, patch
    import httpx

    tool = UrlReaderTool()
    short_markdown = "Short article body."
    mock_resp = httpx.Response(200, text="<html>...</html>", request=httpx.Request("GET", "https://example.com"))

    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch("trafilatura.extract", return_value=short_markdown),
    ):
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client_cls.return_value = mock_client

        result = await tool.execute(url="https://example.com", max_chars=2000)

    assert result.success is True
    assert result.content == short_markdown
    assert "tronqué" not in result.content


@pytest.mark.asyncio
async def test_url_reader_fallback_when_extraction_fails_or_empty() -> None:
    """Ensure pages where trafilatura cannot extract text return informative failure."""
    from unittest.mock import AsyncMock, patch
    import httpx

    tool = UrlReaderTool()
    mock_resp = httpx.Response(200, text="<html><div id='app'></div></html>", request=httpx.Request("GET", "https://example.com/spa"))

    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch("trafilatura.extract", return_value=None),
    ):
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client_cls.return_value = mock_client

        result = await tool.execute(url="https://example.com/spa")

    assert result.success is False
    assert result.error == "ExtractionFailed"
    assert "javascript" in result.content.lower() or "readable text" in result.content.lower()


@pytest.mark.asyncio
async def test_url_reader_handles_http_status_errors() -> None:
    """Ensure HTTP 404 or 403 errors are captured gracefully in ToolResult."""
    from unittest.mock import AsyncMock, patch
    import httpx

    tool = UrlReaderTool()
    req = httpx.Request("GET", "https://example.com/private")
    mock_resp = httpx.Response(403, request=req)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client_cls.return_value = mock_client

        result = await tool.execute(url="https://example.com/private")

    assert result.success is False
    assert "403" in result.content or "HTTP" in str(result.error)


@pytest.mark.asyncio
async def test_url_reader_handles_network_exceptions() -> None:
    """Ensure network timeouts or connection drops do not crash the engine."""
    from unittest.mock import AsyncMock, patch
    import httpx

    tool = UrlReaderTool()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectTimeout("Connection timed out")
        mock_client.__aenter__.return_value = mock_client
        mock_client_cls.return_value = mock_client

        result = await tool.execute(url="https://example.com/offline")

    assert result.success is False
    assert "ConnectTimeout" in str(result.error) or "timeout" in result.content.lower()


