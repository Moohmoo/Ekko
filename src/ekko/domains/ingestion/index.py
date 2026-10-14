"""Ingestion domain façade exposing file/url ingestion and background distillation."""

import asyncio
import hashlib
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ekko.core.models import KnowledgeNote, RawSignal, SignalStatus
from ekko.db.manager import DatabaseManager
from ekko.domains.ingestion.extractors import fetch_web_resource
from ekko.logger import get_logger

logger = get_logger("domains.ingestion")

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB max
VALID_FILE_SUFFIXES = frozenset({".pdf", ".md", ".markdown", ".txt"})


async def prepare_file_ingest(
    db_manager: DatabaseManager,
    file_path_str: str,
) -> tuple[dict[str, Any], Path | None]:
    """Validate local file, perform deduplication, and return initial reply + target path."""
    if not file_path_str:
        raise ValueError("Missing 'file_path' parameter")

    target_path = Path(file_path_str).expanduser().resolve()
    if not target_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {target_path}")
    if not target_path.is_file():
        raise ValueError(f"Le chemin n'est pas un fichier : {target_path}")
    if not os.access(target_path, os.R_OK):
        raise PermissionError(f"Fichier illisible sur le disque (permissions insuffisantes) : {target_path}")

    suffix = target_path.suffix.lower()
    if suffix not in VALID_FILE_SUFFIXES:
        raise ValueError(f"Format non supporté ({suffix}). Formats acceptés : .pdf, .md, .txt")

    # 1. Size guardrail: reject files exceeding 25 MB
    file_size = target_path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        return {
            "status": "rejected",
            "reason": "file_too_large",
            "message": f"Fichier trop volumineux ({file_size} octets > {MAX_FILE_SIZE_BYTES} octets max).",
            "max_bytes": MAX_FILE_SIZE_BYTES,
        }, None

    # 2. SHA-256 deduplication
    try:
        hasher = hashlib.sha256()
        with target_path.open("rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        content_hash = hasher.hexdigest()[:16]
    except Exception as exc:
        logger.warning("Failed to compute SHA-256 for file %s: %s", target_path, exc)
        content_hash = ""

    if content_hash and hasattr(db_manager, "has_content_hash"):
        if await db_manager.has_content_hash(content_hash):
            return {
                "status": "already_exists",
                "filename": target_path.name,
                "content_hash": content_hash,
                "message": "Document déjà indexé dans le coffre.",
            }, None

    # Drop & Forget instant response (< 50ms)
    return {
        "status": "accepted",
        "filename": target_path.name,
        "content_hash": content_hash,
        "message": "Document absorbé · Distillation en cours",
    }, target_path


async def distill_file_background(
    distiller: Any,
    target_path: Path,
    semaphore: asyncio.Semaphore | None = None,
) -> KnowledgeNote:
    """Execute background distillation and note persistence for a local file."""
    if semaphore and getattr(distiller, "semaphore", None) is not semaphore:
        async with semaphore:
            return await distiller.distill_file(target_path)
    return await distiller.distill_file(target_path)


async def prepare_url_ingest(
    db_manager: DatabaseManager,
    url_str: str,
) -> tuple[dict[str, Any], str | None]:
    """Validate web URL, perform deduplication, and return initial reply + URL."""
    clean_url = url_str.strip()
    if not clean_url:
        raise ValueError("Missing 'url' parameter")

    parsed = urlparse(clean_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(
            f"Format d'URL non supporté ou invalide : '{clean_url}'. Seuls http:// et https:// sont acceptés."
        )

    if hasattr(db_manager, "has_source_url"):
        if await db_manager.has_source_url(clean_url):
            return {
                "status": "already_exists",
                "url": clean_url,
                "filename": parsed.netloc,
                "message": "Lien web déjà indexé dans le coffre.",
            }, None

    host = parsed.netloc
    return {
        "status": "accepted",
        "url": clean_url,
        "filename": host,
        "message": f"URL absorbée ({host}) · Distillation en cours",
    }, clean_url


async def distill_url_background(
    distiller: Any,
    url: str,
    semaphore: asyncio.Semaphore | None = None,
) -> KnowledgeNote:
    """Execute background web page fetching and cognitive distillation."""
    content = await fetch_web_resource(url, max_chars=25000)
    parsed = urlparse(url)
    fallback_title = f"{parsed.netloc}{parsed.path}".rstrip("/") or parsed.netloc

    if semaphore and getattr(distiller, "semaphore", None) is not semaphore:
        async with semaphore:
            return await distiller.distill_raw_content(
                raw_content=content,
                title=fallback_title,
                source_id="web_url",
                url=url,
            )
    return await distiller.distill_raw_content(
        raw_content=content,
        title=fallback_title,
        source_id="web_url",
        url=url,
    )


async def distill_signal_background(
    distiller: Any,
    signal_data: dict[str, Any],
    semaphore: asyncio.Semaphore | None = None,
) -> KnowledgeNote:
    """Execute background distillation and note persistence for an archived signal."""
    raw_sig = RawSignal(
        id=str(signal_data["id"]),
        source_id=signal_data.get("source_id") or signal_data.get("source_type") or "signal",
        title=str(signal_data.get("title") or "Signal"),
        url=signal_data.get("url") or signal_data.get("source_url"),
        raw_content=signal_data.get("raw_content"),
        clean_content=signal_data.get("clean_content"),
        status=SignalStatus.ARCHIVED,
    )

    if semaphore and getattr(distiller, "semaphore", None) is not semaphore:
        async with semaphore:
            return await distiller.distill_signal(raw_sig)
    return await distiller.distill_signal(raw_sig)
