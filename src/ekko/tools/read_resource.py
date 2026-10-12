"""ReadResourceTool extracting clean text from web URLs or local filesystem resources."""

import asyncio
from pathlib import Path
import tempfile
import httpx
from pydantic import BaseModel, Field
import trafilatura

from ekko.core.models import ToolResult
from ekko.ingestion.client import HttpFetchError, ResilientHttpClient
from ekko.ingestion.ssrf import SSRFValidator, SSRFViolationError
from ekko.tools.base import BaseTool
from ekko.logger import get_logger

logger = get_logger("tools.read_resource")

TRUNCATION_NOTICE = "\n\n[... Contenu tronqué pour respecter la fenêtre de contexte ...]"


def _truncate_content(text: str, max_chars: int) -> str:
    """Truncate text cleanly to max_chars with a clear notice if exceeded."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + TRUNCATION_NOTICE


def _read_local_file_sync(
    file_path: Path,
    max_chars: int,
    allowed_dirs: list[Path] | None = None,
) -> ToolResult:
    """Read and validate local text file synchronously with path traversal and binary protection."""
    try:
        resolved_target = file_path.expanduser().resolve()
    except Exception as err:
        return ToolResult(content=f"Chemin invalide : {err}", success=False, error="InvalidPath")

    effective_allowed = allowed_dirs or [
        Path.cwd().resolve(),
        Path("data").resolve(),
        Path("data/notes").resolve(),
        Path(tempfile.gettempdir()).resolve(),
    ]

    if not any(resolved_target.is_relative_to(base) for base in effective_allowed):
        logger.warning("Access denied to local file outside allowed perimeter: %s", resolved_target)
        return ToolResult(
            content=f"Accès refusé : le chemin '{file_path}' est hors du périmètre autorisé.",
            success=False,
            error="SecurityViolation",
        )

    if not resolved_target.exists():
        return ToolResult(content=f"Fichier introuvable : {resolved_target}", success=False, error="FileNotFound")
    if not resolved_target.is_file():
        return ToolResult(content=f"Le chemin spécifié n'est pas un fichier : {resolved_target}", success=False, error="NotAFile")

    try:
        with resolved_target.open("rb") as f:
            chunk = f.read(4096)
            if b"\x00" in chunk:
                return ToolResult(content=f"Format binaire non supporté : {resolved_target}", success=False, error="UnsupportedBinary")
        text = resolved_target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ToolResult(content=f"Format binaire ou encodage non supporté : {resolved_target}", success=False, error="UnsupportedBinary")
    except OSError as err:
        return ToolResult(content=f"Erreur de lecture du fichier : {err}", success=False, error="FileReadError")

    return ToolResult(content=_truncate_content(text, max_chars), success=True)


async def _fetch_web_resource(url: str, max_chars: int) -> ToolResult:
    """Fetch and extract web page content as Markdown with resilient SSRF hop-by-hop and error guards."""
    try:
        async with ResilientHttpClient() as client:
            resp = await client.get(url)
            html = resp.text
    except SSRFViolationError as err:
        logger.warning("SSRF violation blocked for URL '%s': %s", url, err)
        return ToolResult(content=f"SSRF error: {err}", success=False, error="SSRFViolationError")
    except (HttpFetchError, httpx.HTTPStatusError) as err:
        return ToolResult(content=f"HTTP error: {err}", success=False, error=type(err).__name__)
    except (httpx.RequestError, Exception) as err:
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

    def __init__(self, allowed_dirs: list[Path | str] | None = None) -> None:
        if allowed_dirs is not None:
            self.allowed_dirs = [Path(d).expanduser().resolve() for d in allowed_dirs]
        else:
            self.allowed_dirs = [
                Path.cwd().resolve(),
                Path("data").resolve(),
                Path("data/notes").resolve(),
                Path(tempfile.gettempdir()).resolve(),
            ]

    async def _run(self, uri: str, max_chars: int = 12000) -> ToolResult:
        """Resolve URI type (web or filesystem) and extract text content safely."""
        cleaned_uri = uri.strip()
        logger.debug("Reading resource from URI: %s", cleaned_uri)

        if cleaned_uri.startswith(("http://", "https://")):
            return await _fetch_web_resource(cleaned_uri, max_chars)

        clean_path = cleaned_uri.removeprefix("file://")
        return await asyncio.to_thread(_read_local_file_sync, Path(clean_path), max_chars, self.allowed_dirs)
