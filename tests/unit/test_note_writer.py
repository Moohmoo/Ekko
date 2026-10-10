"""Unit tests for NoteWriterTool, SaveNoteInput, slugification, and atomic markdown note creation."""

from pathlib import Path
import pytest
from pydantic import ValidationError

from ekko.core.models import ToolResult
from ekko.tools.base import BaseTool
from ekko.tools.note_writer import (
    NoteWriterTool,
    SaveNoteInput,
    _determine_unique_path,
    _format_markdown_note,
    _slugify,
)


def test_save_note_input_valid() -> None:
    """Ensure SaveNoteInput accepts valid inputs and sets proper defaults."""
    data = SaveNoteInput(
        title="Mistral Large 4 Architecture",
        content="Contenu de la note...",
        tags=["ai", "llm"],
        sources=["https://mistral.ai/news/ml4"],
    )
    assert data.title == "Mistral Large 4 Architecture"
    assert data.content == "Contenu de la note..."
    assert data.tags == ["ai", "llm"]
    assert data.sources == ["https://mistral.ai/news/ml4"]


def test_save_note_input_defaults() -> None:
    """Ensure tags and sources default to empty lists."""
    data = SaveNoteInput(title="Titre minimal", content="Contenu minimal")
    assert data.tags == []
    assert data.sources == []


def test_save_note_input_validation_empty_fields() -> None:
    """Ensure empty title or content raises ValidationError."""
    with pytest.raises(ValidationError):
        SaveNoteInput(title="", content="Texte")

    with pytest.raises(ValidationError):
        SaveNoteInput(title="   ", content="Texte")

    with pytest.raises(ValidationError):
        SaveNoteInput(title="Titre", content="")


def test_note_writer_tool_contract() -> None:
    """Ensure NoteWriterTool adheres to BaseTool protocol and exposes schema."""
    tool = NoteWriterTool()
    assert isinstance(tool, BaseTool)
    assert tool.name == "save_note"
    assert tool.args_schema is SaveNoteInput
    assert "sauvegarde" in tool.description.lower() or "enregistre" in tool.description.lower()

    schema = tool.get_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "save_note"
    assert "parameters" in schema["function"]
    props = schema["function"]["parameters"]["properties"]
    assert "title" in props
    assert "content" in props
    assert "tags" in props
    assert "sources" in props


@pytest.mark.parametrize(
    "raw_title,expected_slug",
    [
        ("Mistral Large 4", "mistral-large-4"),
        ("AlphaFold 3: Structure & Design!", "alphafold-3-structure-design"),
        ("Modèle d'ADN & Protéines", "modele-dadn-proteines"),
        ("---Multi---Dash---", "multi-dash"),
        ("   Espaces   Multiples   ", "espaces-multiples"),
        ("Special @#$% Characters", "special-characters"),
        ("", "note"),
    ],
)
def test_slugify(raw_title: str, expected_slug: str) -> None:
    """Ensure titles are cleanly converted to url/filesystem safe slugs."""
    assert _slugify(raw_title) == expected_slug


def test_format_markdown_note() -> None:
    """Ensure generated markdown contains strict YAML frontmatter and title heading."""
    rendered = _format_markdown_note(
        title="Mistral Large 4",
        content="Analyse technique complète.",
        tags=["ai", "llm"],
        sources=["https://mistral.ai/ml4"],
        date_str="2026-10-09",
    )
    expected_header = """---
title: "Mistral Large 4"
date: 2026-10-09
tags:
  - ai
  - llm
sources:
  - "https://mistral.ai/ml4"
---

# Mistral Large 4

Analyse technique complète."""
    assert rendered.strip() == expected_header.strip()


def test_format_markdown_note_empty_tags_and_sources() -> None:
    """Ensure frontmatter handles empty lists without syntax corruption."""
    rendered = _format_markdown_note(
        title="Note Simple",
        content="Corps de la note.",
        tags=[],
        sources=[],
        date_str="2026-10-09",
    )
    assert 'title: "Note Simple"' in rendered
    assert "date: 2026-10-09" in rendered
    assert "tags: []" in rendered
    assert "sources: []" in rendered
    assert "# Note Simple\n\nCorps de la note." in rendered


def test_determine_unique_path_collision_avoidance(tmp_path: Path) -> None:
    """Ensure collisions are avoided by appending incremental suffixes."""
    # First file does not exist yet
    path1 = _determine_unique_path(tmp_path, "test-note", date_str="2026-10-09")
    assert path1.name == "2026-10-09_test-note.md"

    # Simulate path1 created
    path1.write_text("existing", encoding="utf-8")

    # Second file should increment to _1.md
    path2 = _determine_unique_path(tmp_path, "test-note", date_str="2026-10-09")
    assert path2.name == "2026-10-09_test-note_1.md"

    # Simulate path2 created
    path2.write_text("existing", encoding="utf-8")

    # Third file should increment to _2.md
    path3 = _determine_unique_path(tmp_path, "test-note", date_str="2026-10-09")
    assert path3.name == "2026-10-09_test-note_2.md"


@pytest.mark.asyncio
async def test_note_writer_run_nominal(tmp_path: Path) -> None:
    """Ensure NoteWriterTool writes note cleanly to target notes directory."""
    tool = NoteWriterTool(notes_dir=tmp_path)
    result = await tool._run(
        title="DNA Folding Analysis",
        content="Synthèse approfondie sur le repliement de séquences.",
        tags=["bio", "dna"],
        sources=["https://arxiv.org/abs/2610.12345"],
    )

    assert result.success is True
    assert "Note enregistrée avec succès" in result.content
    assert "2026-" in result.content

    files = list(tmp_path.glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert 'title: "DNA Folding Analysis"' in content
    assert "Synthèse approfondie" in content


@pytest.mark.asyncio
async def test_note_writer_security_path_traversal(tmp_path: Path) -> None:
    """Ensure path traversal attempts are safely quarantined within notes_dir."""
    tool = NoteWriterTool(notes_dir=tmp_path)
    result = await tool._run(
        title="../../etc/passwd",
        content="Contenu malveillant.",
    )

    # Slugification turns '../../etc/passwd' into 'etc-passwd'
    assert result.success is True
    assert not Path("/etc/passwd.md").exists()

    files = list(tmp_path.glob("*.md"))
    assert len(files) == 1
    assert files[0].resolve().is_relative_to(tmp_path.resolve())
    assert "etc-passwd" in files[0].name


@pytest.mark.asyncio
async def test_note_writer_explicit_path_traversal_rejection(tmp_path: Path) -> None:
    """Ensure that if an absolute escape path is directly injected, it is blocked."""
    tool = NoteWriterTool(notes_dir=tmp_path)

    # Monkeypatch slugify to simulate an evasion bypass returning path separators
    import ekko.tools.note_writer as nw
    original_slugify = nw._slugify
    try:
        nw._slugify = lambda t: "../escaped_note"
        result = await tool._run(title="malicious", content="malicious")
        assert result.success is False
        assert result.error == "SecurityViolation"
        assert "Accès refusé" in result.content
    finally:
        nw._slugify = original_slugify


@pytest.mark.asyncio
async def test_note_writer_with_hybrid_memory_injection(tmp_path: Path) -> None:
    """Ensure NoteWriterTool persists note to disk and updates hybrid store and embeddings."""
    from unittest.mock import AsyncMock, MagicMock

    mock_db = MagicMock()
    mock_db.save_knowledge_note = AsyncMock()
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1] * 384

    tool = NoteWriterTool(notes_dir=tmp_path, db_manager=mock_db, embedder=mock_embedder)
    result = await tool._run(
        title="CRISPR Analysis",
        content="Research into gene targeting precision.",
        tags=["bio", "crispr"],
        sources=["https://example.com/crispr"],
    )

    assert result.success is True
    assert "mémoire hybride" in result.content
    assert mock_db.save_knowledge_note.call_count == 1
    call_args = mock_db.save_knowledge_note.call_args
    saved_note = call_args[0][0]
    assert saved_note.title == "CRISPR Analysis"
    assert saved_note.tags == ["bio", "crispr"]
    assert call_args[1]["embedding"] == [0.1] * 384
