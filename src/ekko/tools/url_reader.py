"""UrlReaderTool extracting clean Markdown content from web URLs."""

from typing import Any
import httpx
from pydantic import BaseModel, Field, HttpUrl
import trafilatura

from ekko.core.models import ToolResult
from ekko.tools.base import BaseTool
from ekko.utils.logger import get_logger

logger = get_logger("tools.url_reader")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)
TRUNCATION_NOTICE = "\n\n[... Contenu tronqué pour respecter la fenêtre de contexte ...]"


def _truncate_content(text: str, max_chars: int) -> str:
    """Truncate markdown text cleanly to max_chars with a clear notice if exceeded."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + TRUNCATION_NOTICE


async def _fetch_html(url: str) -> str:
    """Fetch raw HTML string using httpx with standard browser headers."""
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(
        timeout=10.0,
        follow_redirects=True,
        headers=headers,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


class UrlReaderInput(BaseModel):
    """Input parameters for reading and extracting clean text from a web URL."""

    url: HttpUrl = Field(
        ...,
        description="The absolute HTTP or HTTPS URL of the web page or article to read.",
    )
    max_chars: int = Field(
        default=12000,
        ge=1000,
        le=100000,
        description="Maximum character limit for the extracted content to protect LLM context (default: 12000).",
    )


class UrlReaderTool(BaseTool):
    """Tool downloading and extracting clean, readable Markdown content from web URLs."""

    name: str = "url_reader"
    description: str = (
        "Extracts clean, readable Markdown content from a given web URL for in-depth analysis."
    )
    args_schema: type[BaseModel] = UrlReaderInput

    async def _run(self, url: HttpUrl, max_chars: int = 12000, **kwargs: Any) -> ToolResult:
        """Fetch and extract web page content as Markdown with context protection."""
        url_str = str(url)
        logger.debug("Fetching URL: %s", url_str)
        try:
            html = await _fetch_html(url_str)
        except httpx.HTTPStatusError as err:
            logger.warning("HTTP error for '%s': %s", url_str, err)
            return ToolResult(
                content=f"HTTP {err.response.status_code} error: {err}",
                success=False,
                error=type(err).__name__,
            )
        except httpx.RequestError as err:
            logger.warning("Network failure for '%s': %s", url_str, err)
            return ToolResult(
                content=f"Network error: {err}",
                success=False,
                error=type(err).__name__,
            )

        markdown = trafilatura.extract(html, output_format="markdown", include_links=True)
        if not markdown or not markdown.strip():
            return ToolResult(
                content="Could not extract readable text from this page (it may require JavaScript rendering).",
                success=False,
                error="ExtractionFailed",
            )

        return ToolResult(content=_truncate_content(markdown, max_chars), success=True)
