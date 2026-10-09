"""Unit tests for ArxivTool and ArxivInput validation schema."""

from unittest.mock import AsyncMock, patch
import httpx
import pytest
from pydantic import ValidationError

from ekko.core.models import ToolResult
from ekko.tools.arxiv import (
    ArxivInput,
    ArxivTool,
    _build_search_query,
    _format_authors,
    _parse_atom_feed,
)
from ekko.tools.base import BaseTool

SAMPLE_ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title type="html">arXiv Query: cat:cs.AI</title>
  <entry>
    <id>http://arxiv.org/abs/2610.12345v1</id>
    <published>2026-10-08T12:00:00Z</published>
    <title>
      Direct Preference Optimization for
      DNA Language Models
    </title>
    <summary>
      We present a comprehensive framework
      for biological sequence fine-tuning using DPO.
      Our method outperforms existing baselines significantly on promoter strength tasks.
    </summary>
    <author><name>Alice Dupont</name></author>
    <author><name>Bob Martin</name></author>
    <author><name>Charlie Smith</name></author>
    <author><name>Dana White</name></author>
    <link href="http://arxiv.org/abs/2610.12345v1" rel="alternate" type="text/html"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2610.54321v1</id>
    <published>2026-10-07T08:30:00Z</published>
    <title>Generative Protein Folding with Diffusion</title>
    <summary>A fast diffusion model generating full 3D atomic structures.</summary>
    <author><name>Eve Adams</name></author>
    <link href="http://arxiv.org/abs/2610.54321v1" rel="alternate" type="text/html"/>
  </entry>
</feed>
"""

EMPTY_ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title type="html">arXiv Query</title>
</feed>
"""


def test_arxiv_input_defaults() -> None:
    """Ensure default values align with targeted research domains."""
    params = ArxivInput()
    assert params.query is None
    assert params.categories == ["cs.AI", "cs.LG", "q-bio.QM", "q-bio.GN", "q-bio.BM"]
    assert params.limit == 5


def test_arxiv_input_custom_valid_values() -> None:
    """Ensure custom valid parameters pass validation cleanly."""
    params = ArxivInput(
        query="protein folding",
        categories=["q-bio.BM"],
        limit=10,
    )
    assert params.query == "protein folding"
    assert params.categories == ["q-bio.BM"]
    assert params.limit == 10


@pytest.mark.parametrize("invalid_limit", [0, -1, 11, 20])
def test_arxiv_input_limit_bounds(invalid_limit: int) -> None:
    """Ensure limit is strictly constrained between 1 and 10."""
    with pytest.raises(ValidationError):
        ArxivInput(limit=invalid_limit)


def test_arxiv_tool_contract() -> None:
    """Ensure ArxivTool satisfies BaseTool interface and exposes proper metadata."""
    tool = ArxivTool()
    assert isinstance(tool, BaseTool)
    assert tool.name == "arxiv"
    assert tool.args_schema is ArxivInput
    assert "arxiv" in tool.description.lower()

    schema = tool.get_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "arxiv"
    parameters = schema["function"]["parameters"]
    assert "properties" in parameters
    assert "query" in parameters["properties"]
    assert "categories" in parameters["properties"]
    assert "limit" in parameters["properties"]


def test_build_search_query_categories_only() -> None:
    """Ensure categories are concatenated with OR when query is None."""
    query = _build_search_query(None, ["cs.AI", "q-bio.QM"])
    assert query == "(cat:cs.AI OR cat:q-bio.QM)"


def test_build_search_query_with_multiword_query() -> None:
    """Ensure multiword query is split into individual all: terms with AND."""
    query = _build_search_query("protein folding", ["q-bio.BM"])
    assert query == "(cat:q-bio.BM) AND (all:protein AND all:folding)"


def test_build_search_query_with_single_word_query() -> None:
    """Ensure single word query is not unnecessarily quoted and properly formatted."""
    query = _build_search_query("crispr", ["q-bio.GN"])
    assert query == '(cat:q-bio.GN) AND all:crispr'


def test_build_search_query_no_categories_with_query() -> None:
    """Ensure query alone works when categories list is empty."""
    query = _build_search_query("alphafold", [])
    assert query == "all:alphafold"


def test_format_authors_condensation() -> None:
    """Ensure author list keeps max 3 and appends et al. when exceeding 3."""
    assert _format_authors(["Alice", "Bob"]) == "Alice, Bob"
    assert _format_authors(["Alice", "Bob", "Charlie"]) == "Alice, Bob, Charlie"
    assert _format_authors(["Alice", "Bob", "Charlie", "Dana", "Eve"]) == "Alice, Bob, Charlie et al."
    assert _format_authors([]) == "Auteurs inconnus"


def test_parse_atom_feed_nominal() -> None:
    """Ensure Atom XML entries are accurately converted to condensed markdown."""
    result = _parse_atom_feed(SAMPLE_ATOM_FEED)
    assert "Direct Preference Optimization for DNA Language Models" in result
    assert "Alice Dupont, Bob Martin, Charlie Smith et al." in result
    assert "2026-10-08" in result
    assert "http://arxiv.org/abs/2610.12345v1" in result
    assert "Generative Protein Folding with Diffusion" in result
    assert "Eve Adams" in result


def test_parse_atom_feed_empty() -> None:
    """Ensure empty feed returns informative message."""
    result = _parse_atom_feed(EMPTY_ATOM_FEED)
    assert result == "Aucune prépublication récente trouvée sur arXiv pour ces critères."


def test_parse_atom_feed_truncates_long_summary() -> None:
    """Ensure abstracts exceeding 700 characters are safely clipped with ellipsis."""
    long_abstract = "A" * 900
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2610.99999v1</id>
    <published>2026-10-08T00:00:00Z</published>
    <title>Long paper</title>
    <summary>{long_abstract}</summary>
    <author><name>Author</name></author>
  </entry>
</feed>
"""
    result = _parse_atom_feed(xml)
    assert "..." in result
    # Abstract should not contain the full 900 chars
    assert "A" * 900 not in result
    assert "A" * 700 in result


@pytest.mark.asyncio
async def test_arxiv_tool_run_nominal() -> None:
    """Ensure ArxivTool._run calls httpx client with expected params and headers."""
    tool = ArxivTool()
    mock_response = httpx.Response(
        200,
        text=SAMPLE_ATOM_FEED,
        request=httpx.Request("GET", "https://export.arxiv.org/api/query"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await tool._run(query="DNA Models", limit=2)

    assert result.success is True
    assert "DNA Language Models" in result.content
    mock_get.assert_called_once()
    call_args, call_kwargs = mock_get.call_args
    assert call_args[0] == "https://export.arxiv.org/api/query"
    params = call_kwargs["params"]
    assert params["sortBy"] == "submittedDate"
    assert params["sortOrder"] == "descending"
    assert params["max_results"] == 2
    assert "Ekko" in call_kwargs["headers"]["User-Agent"]


@pytest.mark.asyncio
async def test_arxiv_tool_run_http_status_error() -> None:
    """Ensure HTTP errors like 429/503 are captured gracefully as ToolResult failures."""
    tool = ArxivTool()
    mock_response = httpx.Response(
        503,
        request=httpx.Request("GET", "https://export.arxiv.org/api/query"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPStatusError("Service Unavailable", request=mock_response.request, response=mock_response)
        result = await tool._run(query="test")

    assert result.success is False
    assert result.error == "ArxivHttpError"
    assert "503" in result.content


@pytest.mark.asyncio
async def test_arxiv_tool_run_network_error() -> None:
    """Ensure connection drops or timeouts return clean ToolResult without unhandled crash."""
    tool = ArxivTool()

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectTimeout("Connection timeout to arXiv")
        result = await tool._run(query="test")

    assert result.success is False
    assert result.error == "ArxivNetworkError"
    assert "inaccessible" in result.content


@pytest.mark.asyncio
async def test_arxiv_tool_run_xml_parse_error() -> None:
    """Ensure invalid or malformed XML returns clean ToolResult."""
    tool = ArxivTool()
    mock_response = httpx.Response(
        200,
        text="<feed><entry><title>Unclosed tag</entry>",
        request=httpx.Request("GET", "https://export.arxiv.org/api/query"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await tool._run(query="test")

    assert result.success is False
    assert result.error == "ArxivParseError"
    assert "XML" in result.content
