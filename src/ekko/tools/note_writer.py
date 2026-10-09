"""NoteWriterTool for persisting intelligence and research notes in Markdown with YAML frontmatter."""

import asyncio
from datetime import datetime
from pathlib import Path
import re
import unicodedata
from pydantic import BaseModel, Field, field_validator

from ekko.core.models import ToolResult
from ekko.tools.base import BaseTool
from ekko.utils.logger import get_logger

logger = get_logger("tools.note_writer")


class SaveNoteInput(BaseModel):
    """Input parameters for saving an intelligence note to local Markdown storage."""

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


def _slugify(text: str) -> str:
    """Normalize text into an alphanumeric filesystem-safe slug."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    # Replace slashes and path separators with dash to prevent path traversal
    text = re.sub(r"[/\\.]+", "-", text)
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text if text else "note"


def _format_markdown_note(
    title: str,
    content: str,
    tags: list[str],
    sources: list[str],
    date_str: str,
) -> str:
    """Assemble strict YAML frontmatter followed by markdown body."""
    lines: list[str] = ["---", f'title: "{title}"', f"date: {date_str}"]

    if tags:
        lines.append("tags:")
        for t in tags:
            lines.append(f"  - {t}")
    else:
        lines.append("tags: []")

    if sources:
        lines.append("sources:")
        for s in sources:
            lines.append(f'  - "{s}"')
    else:
        lines.append("sources: []")

    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")
    lines.append(content.strip())
    lines.append("")

    return "\n".join(lines)


def _determine_unique_path(base_dir: Path, slug: str, date_str: str) -> Path:
    """Determine non-colliding file path with incremental suffix if needed."""
    candidate = base_dir / f"{date_str}_{slug}.md"
    if not candidate.exists():
        return candidate

    counter = 1
    while True:
        candidate = base_dir / f"{date_str}_{slug}_{counter}.md"
        if not candidate.exists():
            return candidate
        counter += 1


class NoteWriterTool(BaseTool):
    """Save synthesized reports and research notes into local Markdown files."""

    name: str = "save_note"
    description: str = (
        "Enregistre une note de veille ou synthèse technique au format Markdown avec en-tête "
        "YAML (frontmatter) dans le répertoire local de notes (compatible Obsidian / PKM)."
    )
    args_schema: type[BaseModel] = SaveNoteInput

    def __init__(self, notes_dir: Path | str = "notes") -> None:
        self.notes_dir = Path(notes_dir)

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
        """Format, validate security confinement, and save note to filesystem."""
        resolved_base = self.notes_dir.resolve()
        date_str = datetime.now().strftime("%Y-%m-%d")
        slug = _slugify(title)

        if "/" in slug or "\\" in slug or ".." in slug:
            logger.error("Security violation: invalid characters in slug '%s'", slug)
            return ToolResult(
                content=f"Accès refusé : tentative d'écriture hors du répertoire autorisé ({self.notes_dir}).",
                success=False,
                error="SecurityViolation",
            )

        try:
            target_path = _determine_unique_path(resolved_base, slug, date_str)
            resolved_target = target_path.resolve()

            # Strict path containment check
            if not resolved_target.is_relative_to(resolved_base):
                logger.error(
                    "Security violation: path traversal detected (%s outside %s)",
                    resolved_target,
                    resolved_base,
                )
                return ToolResult(
                    content=f"Accès refusé : tentative d'écriture hors du répertoire autorisé ({self.notes_dir}).",
                    success=False,
                    error="SecurityViolation",
                )
        except Exception as exc:
            logger.error("Path validation error: %s", exc)
            return ToolResult(
                content=f"Chemin invalide : {exc}",
                success=False,
                error="InvalidPath",
            )

        note_text = _format_markdown_note(
            title=title,
            content=content,
            tags=tags or [],
            sources=sources or [],
            date_str=date_str,
        )

        try:
            await asyncio.to_thread(self._write_file_sync, resolved_target, note_text)
            rel_display = resolved_target.relative_to(Path.cwd()) if resolved_target.is_relative_to(Path.cwd()) else resolved_target
            logger.info("Note successfully written to %s", rel_display)
            return ToolResult(
                content=f"Note enregistrée avec succès sous : {rel_display}",
                success=True,
            )
        except OSError as exc:
            logger.error("Filesystem write error: %s", exc)
            return ToolResult(
                content=f"Erreur d'écriture sur le disque : {exc}",
                success=False,
                error="DiskWriteError",
            )
