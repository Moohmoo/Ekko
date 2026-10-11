"""Autonomous background distillation service extracting insights from pending raw signals."""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from ekko.core.models import Message
from ekko.core.ports import HybridMemoryPort, LLMProviderPort
from ekko.daemon.resources import ResourceManager
from ekko.logger import get_logger
from ekko.memory.models import KnowledgeNote, RawSignal
from ekko.tools.note_writer import (
    _determine_unique_path,
    _format_markdown_note,
    _slugify,
)

logger = get_logger("daemon.distiller")


def _build_distill_prompt(signal: RawSignal) -> str:
    """Build a concise, strict distillation prompt requesting JSON output."""
    content = signal.clean_content or signal.raw_content
    return (
        "You are Ekko's cognitive distillation engine. Extract insights from this signal:\n"
        f"Title: {signal.title}\n"
        f"Source: {signal.source_id}\n"
        f"Content:\n{content[:4000]}\n\n"
        "Return ONLY a JSON object with this exact structure:\n"
        "{\n"
        '  "title": "Refined and concise title",\n'
        '  "summary": "2-3 sentences summarizing key insight",\n'
        '  "key_points": ["Point 1", "Point 2", "Point 3"],\n'
        '  "tags": ["tag1", "tag2"]\n'
        "}"
    )


def _parse_distillation(response_text: str, default_title: str) -> tuple[str, str, str, list[str]]:
    """Parse JSON or extract structured summary fallback from model response."""
    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            title = data.get("title") or default_title
            summary = data.get("summary") or ""
            points = data.get("key_points") or []
            tags = data.get("tags") or ["distilled"]
            body = f"## Summary\n\n{summary}\n\n## Key Takeaways\n\n" + "\n".join(f"- {p}" for p in points)
            return title, summary, body, tags
        except json.JSONDecodeError:
            pass

    summary = response_text.strip()[:300]
    return default_title, summary, response_text.strip(), ["distilled"]


class SignalDistiller:
    """Processes pending raw signals into structured knowledge notes."""

    def __init__(
        self,
        store: HybridMemoryPort,
        llm_provider: LLMProviderPort,
        notes_dir: Path | str = "data/notes",
        embedder: Any | None = None,
    ) -> None:
        self.store = store
        self.llm_provider = llm_provider
        self.notes_dir = Path(notes_dir)
        self.embedder = embedder
        self.resource_manager = ResourceManager()

    def _write_physical_note(self, note: KnowledgeNote, date_str: str, slug: str) -> None:
        """Write note markdown file with YAML frontmatter to notes directory."""
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        # Check if note file with same date and slug already exists
        primary_file = self.notes_dir / f"{date_str}_{slug}.md"
        if primary_file.exists():
            file_path = primary_file
        else:
            file_path = _determine_unique_path(self.notes_dir, slug, date_str)
        text = _format_markdown_note(note.title, note.content, note.tags, note.sources, date_str)
        file_path.write_text(text, encoding="utf-8")

    async def _persist_note(
        self,
        signal: RawSignal,
        title: str,
        summary: str,
        body: str,
        tags: list[str],
    ) -> KnowledgeNote:
        """Save knowledge note in hybrid store and on disk, ensuring idempotence."""
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        slug = _slugify(title)
        sources = [signal.url] if signal.url else [signal.source_id]

        note = KnowledgeNote(
            id=f"note_{slug}",
            slug=f"{date_str}_{slug}",
            title=title,
            summary=summary,
            content=body,
            tags=tags,
            sources=sources,
            created_at=now,
            updated_at=now,
        )
        vec = self.embedder.embed_query(f"{title}\n{body}") if self.embedder else None
        await self.store.save_knowledge_note(note, embedding=vec)
        await asyncio.to_thread(self._write_physical_note, note, date_str, slug)
        return note

    async def _distill_single_signal(self, signal: RawSignal) -> KnowledgeNote:
        """Run LLM inference with VRAM confinement and save distilled note."""
        prompt = _build_distill_prompt(signal)
        messages = [Message(role="user", content=prompt)]
        call_kwargs = self.resource_manager.inject_unload_vram()

        response = await self.llm_provider.generate(messages, **call_kwargs)
        title, summary, body, tags = _parse_distillation(response.content, signal.title)
        return await self._persist_note(signal, title, summary, body, tags)

    async def distill_batch(self, batch_size: int = 5) -> int:
        """Fetch pending signals, distill them, and transition states."""
        signals = await self.store.get_pending_signals(limit=batch_size)
        if not signals:
            return 0

        success_count = 0
        for signal in signals:
            try:
                await self._distill_single_signal(signal)
                await self.store.mark_signal_status(signal.id, "processed")
                success_count += 1
                logger.info("Signal '%s' distilled successfully into note.", signal.id)
            except Exception as exc:
                logger.error("Failed to distill signal '%s': %s", signal.id, exc)
                await self.store.mark_signal_status(signal.id, "failed")

        return success_count
