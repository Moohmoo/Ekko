"""Document and text extractors decoupling file reading from cognitive distillation."""

from pathlib import Path

from ekko.core.errors import DistillationError


def extract_text_from_file(file_path: Path | str) -> tuple[str, str]:
    """Extract clean text content and title from a local file (.pdf, .md, .txt).

    Returns:
        tuple[str, str]: (extracted_text, document_title)

    Raises:
        DistillationError: If the file does not exist, is unreadable, or extraction fails.
    """
    path = Path(file_path)
    if not path.exists():
        raise DistillationError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import pypdf

            reader = pypdf.PdfReader(str(path))
            extracted_text = "".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise DistillationError(f"Failed to extract PDF text from '{path}': {exc}") from exc
    else:
        try:
            extracted_text = path.read_text(encoding="utf-8")
        except Exception as exc:
            raise DistillationError(f"Failed to read file '{path}': {exc}") from exc

    cleaned = extracted_text.strip()
    if not cleaned:
        raise DistillationError(f"File '{path}' contains no extractable text")

    title = path.stem.replace("_", " ").replace("-", " ").title()
    return cleaned, title


async def fetch_web_resource(url: str, max_chars: int = 25000) -> str:
    """Fetch and extract web page content as Markdown with resilient SSRF and error guards."""
    import httpx
    import trafilatura
    from ekko.domains.ingestion.client import ResilientHttpClient

    try:
        async with ResilientHttpClient() as client:
            resp = await client.get(url)
            html = resp.text
    except Exception as err:
        raise DistillationError(f"Failed to fetch web content from '{url}': {err}") from err

    markdown = trafilatura.extract(html, output_format="markdown", include_links=True)
    if not markdown or not markdown.strip():
        raise DistillationError(f"Could not extract readable text from '{url}' (it may require JavaScript rendering).")

    return markdown[:max_chars].strip()

