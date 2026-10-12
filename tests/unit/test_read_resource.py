"""Unit tests for ReadResourceTool contract, URI routing, web and filesystem extraction."""

from pathlib import Path
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from pydantic import ValidationError

from ekko.core.ports import ToolPort
from ekko.tools.read_resource import ReadResourceInput, ReadResourceTool


def test_read_resource_implements_tool_port() -> None:
    """Ensure ReadResourceTool satisfies ToolPort protocol."""
    tool = ReadResourceTool()
    assert isinstance(tool, ToolPort)
    assert tool.name == "read_resource"
    assert "ressource" in tool.description.lower() or "url" in tool.description.lower()


def test_read_resource_input_defaults() -> None:
    """Ensure valid URI is accepted and max_chars defaults to 12000."""
    schema = ReadResourceInput(uri="https://example.com/article")
    assert schema.uri == "https://example.com/article"
    assert schema.max_chars == 12000


def test_read_resource_input_validation_bounds() -> None:
    """Ensure out-of-bound max_chars are rejected."""
    with pytest.raises(ValidationError):
        ReadResourceInput()  # type: ignore[call-arg]

    with pytest.raises(ValidationError):
        ReadResourceInput(uri="https://example.com", max_chars=999)

    with pytest.raises(ValidationError):
        ReadResourceInput(uri="https://example.com", max_chars=100001)


def test_read_resource_json_schema() -> None:
    """Ensure generated schema exposes uri (required) and max_chars."""
    tool = ReadResourceTool()
    schema = tool.get_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "read_resource"

    parameters = schema["function"]["parameters"]
    assert parameters["type"] == "object"
    props = parameters["properties"]
    assert "uri" in props
    assert "max_chars" in props
    assert "uri" in parameters["required"]


@pytest.mark.asyncio
async def test_read_resource_web_nominal_fetch_and_markdown() -> None:
    """Ensure HTTP client fetches URL and extracts Markdown via Trafilatura."""
    tool = ReadResourceTool()
    sample_html = "<html><body><article><h1>Quantum Leap</h1><p>Discovery in physics.</p></article></body></html>"
    expected_markdown = "# Quantum Leap\n\nDiscovery in physics."

    mock_resp = httpx.Response(
        200,
        text=sample_html,
        request=httpx.Request("GET", "https://example.com/physics"),
    )

    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch("trafilatura.extract") as mock_extract,
        patch("ekko.tools.read_resource.SSRFValidator.validate_url", return_value="https://example.com/physics"),
    ):
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client_cls.return_value = mock_client
        mock_extract.return_value = expected_markdown

        result = await tool.execute(uri="https://example.com/physics")

        assert result.success is True
        assert result.content == expected_markdown


@pytest.mark.asyncio
async def test_read_resource_web_ssrf_blocking() -> None:
    """Ensure SSRF attempt triggers blocked ToolResult."""
    tool = ReadResourceTool()
    result = await tool.execute(uri="http://127.0.0.1:8000/secret")
    assert result.success is False
    assert result.error == "SSRFViolationError"


@pytest.mark.asyncio
async def test_read_resource_truncates_when_exceeding_max_chars() -> None:
    """Ensure content exceeding max_chars is cleanly truncated with notice."""
    tool = ReadResourceTool()
    long_markdown = "A" * 5000
    mock_resp = httpx.Response(200, text="<html>...</html>", request=httpx.Request("GET", "https://example.com"))

    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch("trafilatura.extract", return_value=long_markdown),
        patch("ekko.tools.read_resource.SSRFValidator.validate_url", return_value="https://example.com"),
    ):
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client_cls.return_value = mock_client

        result = await tool.execute(uri="https://example.com", max_chars=2000)

    assert result.success is True
    assert result.content.startswith("A" * 2000)
    assert "tronqué" in result.content


@pytest.mark.asyncio
async def test_read_resource_local_file_reading(tmp_path: Path) -> None:
    """Ensure local text and markdown files can be read cleanly."""
    tool = ReadResourceTool()
    doc_path = tmp_path / "notes.md"
    doc_path.write_text("# Obsidian Note\nImportant findings.", encoding="utf-8")

    result = await tool.execute(uri=str(doc_path))
    assert result.success is True
    assert "# Obsidian Note" in result.content

    # Test file:// prefix
    result_scheme = await tool.execute(uri=f"file://{doc_path}")
    assert result_scheme.success is True
    assert "# Obsidian Note" in result_scheme.content


@pytest.mark.asyncio
async def test_read_resource_local_file_not_found(tmp_path: Path) -> None:
    """Ensure missing local file returns FileNotFound error."""
    tool = ReadResourceTool()
    missing_path = tmp_path / "does_not_exist.txt"

    result = await tool.execute(uri=str(missing_path))
    assert result.success is False
    assert result.error == "FileNotFound"
    assert "introuvable" in result.content


@pytest.mark.asyncio
async def test_read_resource_local_directory_error(tmp_path: Path) -> None:
    """Ensure pointing to a directory returns NotAFile error."""
    tool = ReadResourceTool()
    result = await tool.execute(uri=str(tmp_path))
    assert result.success is False
    assert result.error == "NotAFile"


@pytest.mark.asyncio
async def test_read_resource_local_binary_rejection(tmp_path: Path) -> None:
    """Ensure binary files with null bytes are rejected cleanly."""
    tool = ReadResourceTool()
    bin_file = tmp_path / "binary.dat"
    bin_file.write_bytes(b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00")

    result = await tool.execute(uri=str(bin_file))
    assert result.success is False
    assert result.error == "UnsupportedBinary"
    assert "binaire" in result.content


@pytest.mark.asyncio
async def test_read_resource_web_http_error() -> None:
    """Ensure HTTP errors are returned cleanly."""
    tool = ReadResourceTool()
    req = httpx.Request("GET", "https://example.com/err")
    mock_resp = httpx.Response(404, request=req)

    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch("ekko.tools.read_resource.SSRFValidator.validate_url", return_value="https://example.com/err"),
    ):
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client_cls.return_value = mock_client

        result = await tool.execute(uri="https://example.com/err")

    assert result.success is False
    assert "404" in result.content


@pytest.mark.asyncio
async def test_read_resource_path_traversal_rejection() -> None:
    """Ensure path traversal attempts to read sensitive system files are rejected."""
    tool = ReadResourceTool()
    # Test absolute system path
    result_abs = await tool.execute(uri="/etc/passwd")
    assert result_abs.success is False
    assert result_abs.error == "SecurityViolation"
    assert "hors du périmètre autorisé" in result_abs.content

    # Test relative traversal escape
    result_rel = await tool.execute(uri="../../../../etc/passwd")
    assert result_rel.success is False
    assert result_rel.error == "SecurityViolation"
    assert "hors du périmètre autorisé" in result_rel.content


@pytest.mark.asyncio
async def test_read_resource_symlink_traversal_rejection(tmp_path: Path) -> None:
    """Ensure symlinks pointing outside allowed sandbox are rejected via canonical resolution."""
    tool = ReadResourceTool()
    symlink_file = tmp_path / "evil_symlink.txt"
    try:
        symlink_file.symlink_to("/etc/passwd")
    except OSError:
        pytest.skip("Symlink creation not permitted in current environment")

    result = await tool.execute(uri=str(symlink_file))
    assert result.success is False
    assert result.error == "SecurityViolation"
    assert "hors du périmètre autorisé" in result.content


@pytest.mark.asyncio
async def test_read_resource_custom_sandbox_confinement(tmp_path: Path) -> None:
    """Ensure custom allowed_dirs sandboxes access strictly to specified roots."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    allowed_doc = sandbox / "allowed.txt"
    allowed_doc.write_text("Secret in sandbox", encoding="utf-8")

    forbidden = tmp_path / "forbidden"
    forbidden.mkdir()
    forbidden_doc = forbidden / "forbidden.txt"
    forbidden_doc.write_text("Secret outside sandbox", encoding="utf-8")

    tool = ReadResourceTool(allowed_dirs=[sandbox])

    # Reading within sandbox succeeds
    res_ok = await tool.execute(uri=str(allowed_doc))
    assert res_ok.success is True
    assert "Secret in sandbox" in res_ok.content

    # Reading outside sandbox fails even though file exists
    res_blocked = await tool.execute(uri=str(forbidden_doc))
    assert res_blocked.success is False
    assert res_blocked.error == "SecurityViolation"


@pytest.mark.asyncio
async def test_read_resource_redirect_ssrf_rejection() -> None:
    """Ensure malicious HTTP redirects to internal/private addresses trigger SSRFViolationError."""
    from ekko.ingestion.ssrf import SSRFViolationError

    tool = ReadResourceTool()
    with patch("ekko.tools.read_resource.ResilientHttpClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = SSRFViolationError("Redirect hop to private IP 127.0.0.1 blocked")
        mock_client.__aenter__.return_value = mock_client
        mock_client_cls.return_value = mock_client

        result = await tool.execute(uri="https://attacker.com/redirect-to-localhost")
        assert result.success is False
        assert result.error == "SSRFViolationError"
        assert "SSRF error" in result.content
