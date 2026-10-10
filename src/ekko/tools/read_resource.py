"""ReadResourceTool extracting clean text from web URLs or local filesystem resources."""

import asyncio
from pathlib import Path
from typing import Any
import httpx
from pydantic import BaseModel, Field
import trafilatura

from ekko.core.models import ToolResult
from ekko.ingestion.ssrf import SSRFValidator, SSRFViolationError
from ekko.tools.base import BaseTool
from ekko.logger import get_logger

logger = get_logger("tools.read_resource")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)
TRUNCATION_NOTICE = "\n\n[... Contenu tronqué pour respecter la fenêtre de contexte ...]"


def _truncate_content(text: str, max_chars: int) -> str:
    """Truncate text cleanly to max_chars with a clear notice if exceeded."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + TRUNCATION_NOTICE


def _read_local_file_sync(file_path: Path, max_chars: int) -> ToolResult:
    """Read and validate local text file synchronously with binary detection."""
    if not file_path.exists():
        return ToolResult(content=f"Fichier introuvable : {file_path}", success=False, error="FileNotFound")
    if not file_path.is_file():
        return ToolResult(content=f"Le chemin spécifié n'est pas un fichier : {file_path}", success=False, error="NotAFile")

    try:
        with file_path.open("rb") as f:
            chunk = f.read(4096)
            if b"\x00" in chunk:
                return ToolResult(content=f"Format binaire non supporté : {file_path}", success=False, error="UnsupportedBinary")
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ToolResult(content=f"Format binaire ou encodage non supporté : {file_path}", success=False, error="UnsupportedBinary")
    except OSError as err:
        return ToolResult(content=f"Erreur de lecture du fichier : {err}", success=False, error="FileReadError")

    return ToolResult(content=_truncate_content(text, max_chars), success=True)


async def _fetch_web_resource(url: str, max_chars: int) -> ToolResult:
    """Fetch and extract web page content as Markdown with SSRF and error guards."""
    try:
        safe_url = SSRFValidator().validate_url(url)
    except SSRFViolationError as err:
        logger.warning("SSRF violation blocked for URL '%s': %s", url, err)
        return ToolResult(content=f"SSRF error: {err}", success=False, error="SSRFViolationError")

    headers = {"User-Agent": USER_AGENT}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(safe_url)
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPStatusError as err:
        return ToolResult(content=f"HTTP {err.response.status_code} error: {err}", success=False, error=type(err).__name__)
    except httpx.RequestError as err:
        return ToolResult(content=f"Network error: {err}", success=False, error=type(err).__name__)

    markdown = trafilatura.extract(html, output_format="markdown", include_links=True)
    if not markdown or not markdown.strip():
        return ToolResult(
            content="Could not extract readable text from this page (it may require JavaScript rendering).",
            success=False,
            error="ExtractionFailed",
        )

    return ToolResult(content=_truncate_content(markdown, max_chars), success=True)


class ReadResourceInput(BaseModel):
    """Input parameters for reading a resource (web URL or local file)."""

    uri: str = Field(
        ...,
        description="The URI or path of the resource to read (HTTP/HTTPS URL or local file path).",
    )
    max_chars: int = Field(
        default=12000,
        ge=1000,
        le=100000,
        description="Maximum character limit for the extracted content to protect LLM context (default: 12000).",
    )


class ReadResourceTool(BaseTool):
    """Universal tool extracting text from web URLs or local filesystem paths."""

    name: str = "read_resource"
    description: str = (
        "Lit et extrait le contenu textuel d'une ressource (URL web ou fichier local)."
    )
    args_schema: type[BaseModel] = ReadResourceInput

    async def _run(self, uri: str, max_chars: int = 12000, **kwargs: Any) -> ToolResult:
        """Resolve URI type (web or filesystem) and extract text content safely."""
        cleaned_uri = uri.strip()
        logger.debug("Reading resource from URI: %s", cleaned_uri)

        if cleaned_uri.startswith(("http://", "https://")):
            return await _fetch_web_resource(cleaned_uri, max_chars)

        clean_path = cleaned_uri.removeprefix("file://")
        return await asyncio.to_thread(_read_local_file_sync, Path(clean_path), max_chars)
