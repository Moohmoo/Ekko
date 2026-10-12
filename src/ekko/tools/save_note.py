"""SaveNoteTool persisting notes both to Obsidian Markdown files and the SQLite hybrid store."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any
import unicodedata
from pydantic import BaseModel, Field, field_validator

from ekko.core.models import KnowledgeNote, ToolResult
from ekko.core.ports import HybridMemoryPort
from ekko.tools.base import BaseTool
from ekko.logger import get_logger

logger = get_logger("tools.save_note")


class SaveNoteInput(BaseModel):
    """Input parameters for saving an intelligence note to local Markdown and PKM storage."""

    title: str = Field(
        ...,
        description="Titre concis et informatif de la note (ex: 'Mistral Large 4 Architecture').",
    )
    content: str = Field(
        ...,
        description="Corps complet et structuré de la note en Markdown.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Liste d'étiquettes thématiques associées (ex: ['ai', 'llm', 'bioinformatics']).",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Liste d'URLs ou références sources (ex: ['https://arxiv.org/abs/...']).",
    )

    @field_validator("title", "content")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        """Ensure title and content are not empty or whitespace only."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or only whitespace")
        return cleaned


from ekko.memory.formatters import (
    determine_unique_path as _determine_unique_path,
    format_markdown_note as _format_markdown_note,
    slugify as _slugify,
)


def _build_knowledge_note(
    title: str,
    content: str,
    tags: list[str] | None,
    sources: list[str] | None,
    slug: str,
    date_str: str,
) -> KnowledgeNote:
    """Construct a KnowledgeNote model entity with UTC timestamps."""
    now = datetime.now(timezone.utc)
    paragraphs = [p.strip() for p in content.strip().split("\n\n") if p.strip()]
    summary = paragraphs[0][:300] if paragraphs else title
    return KnowledgeNote(
        id=f"note_{slug}",
        slug=f"{date_str}_{slug}",
        title=title,
        summary=summary,
        content=content,
        tags=tags or [],
        sources=sources or [],
        created_at=now,
        updated_at=now,
    )


async def _sync_hybrid_store(
    db_manager: HybridMemoryPort,
    note: KnowledgeNote,
    embedder: Any | None,
) -> None:
    """Index note into SQLite tables, FTS5 index, and sqlite-vec embeddings."""
    embedding = None
    if embedder is not None and hasattr(embedder, "embed_query"):
        embedding = await asyncio.to_thread(embedder.embed_query, f"{note.title}\n{note.content}")
    await db_manager.save_knowledge_note(note, embedding=embedding)
    logger.info("Note '%s' synced to hybrid memory store.", note.slug)


class SaveNoteTool(BaseTool):
    """Save synthesized reports and research notes into local Markdown files and hybrid DB."""

    name: str = "save_note"
    description: str = (
        "Enregistre une note de veille ou synthèse technique au format Markdown avec en-tête "
        "YAML (frontmatter) dans le coffre local et l'indexe dans la base PKM hybride."
    )
    args_schema: type[BaseModel] = SaveNoteInput

    def __init__(
        self,
        notes_dir: Path | str = "data/notes",
        db_manager: HybridMemoryPort | None = None,
        embedder: Any | None = None,
    ) -> None:
        self.notes_dir = Path(notes_dir)
        self.db_manager = db_manager
        self.embedder = embedder

    def _write_file_sync(self, target_path: Path, note_content: str) -> None:
        """Synchronously write note content to disk ensuring directory existence."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(note_content, encoding="utf-8")

    async def _run(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
        sources: list[str] | None = None,
    ) -> ToolResult:
        """Format, validate security containment, write Markdown and index into hybrid DB."""
        resolved_base = self.notes_dir.resolve()
        date_str = datetime.now().strftime("%Y-%m-%d")
        slug = _slugify(title)

        if "/" in slug or "\\" in slug or ".." in slug:
            return ToolResult(
                content=f"Accès refusé : tentative d'écriture hors du répertoire autorisé ({self.notes_dir}).",
                success=False,
                error="SecurityViolation",
            )

        try:
            target_path = _determine_unique_path(resolved_base, slug, date_str)
            resolved_target = target_path.resolve()
            if not resolved_target.is_relative_to(resolved_base):
                return ToolResult(
                    content=f"Accès refusé : tentative d'écriture hors du répertoire autorisé ({self.notes_dir}).",
                    success=False,
                    error="SecurityViolation",
                )
        except Exception as exc:
            return ToolResult(content=f"Chemin invalide : {exc}", success=False, error="InvalidPath")

        note_text = _format_markdown_note(
            title=title, content=content, tags=tags or [], sources=sources or [], date_str=date_str,
        )

        try:
            await asyncio.to_thread(self._write_file_sync, resolved_target, note_text)
        except OSError as exc:
            return ToolResult(content=f"Erreur d'écriture sur le disque : {exc}", success=False, error="DiskWriteError")

        if self.db_manager is not None:
            knote = _build_knowledge_note(title, content, tags, sources, slug, date_str)
            await _sync_hybrid_store(self.db_manager, knote, self.embedder)

        rel_display = (
            resolved_target.relative_to(Path.cwd())
            if resolved_target.is_relative_to(Path.cwd())
            else resolved_target
        )
        logger.info("Note successfully written to %s", rel_display)
        return ToolResult(
            content=f"Note enregistrée avec succès sous : {rel_display} (indexée dans la mémoire hybride).",
            success=True,
        )
