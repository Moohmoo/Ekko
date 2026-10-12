"""Autonomous background distillation service extracting insights from pending raw signals."""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from ekko.core.errors import DistillationError
from ekko.core.models import KnowledgeNote, Message, RawSignal
from ekko.core.ports import EmbedderPort, HybridMemoryPort, LLMProviderPort, ResourceManagerPort
from ekko.ingestion.compressor import ContentCompressor, ModelProfile
from ekko.ingestion.extractors import extract_text_from_file
from ekko.logger import get_logger
from ekko.memory.formatters import determine_unique_path, format_markdown_note, slugify

logger = get_logger("ingestion.distiller")
_compressor = ContentCompressor()


def _build_distill_prompt(signal: RawSignal) -> str:
    """Build a concise, strict distillation prompt with heuristic pruning and token budgeting."""
    content = signal.clean_content or signal.raw_content
    pruned = _compressor.prune_heuristics(content)
    budgeted = _compressor.truncate_to_budget(
        pruned,
        profile=ModelProfile.STANDARD,
        custom_budget=1000,  # 1000 tokens ~ 4000 characters
    )
    return (
        "You are Ekko's cognitive distillation engine. Extract insights from this signal:\n"
        f"Title: {signal.title}\n"
        f"Source: {signal.source_id}\n"
        f"Content:\n{budgeted}\n\n"
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
    cleaned = response_text.strip()
    if not cleaned:
        raise DistillationError("LLM returned empty distillation response")

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                title = data.get("title") or default_title
                summary = data.get("summary") or ""
                raw_points = data.get("key_points")
                points = [str(p) for p in raw_points] if isinstance(raw_points, list) else []
                raw_tags = data.get("tags")
                tags = [str(t) for t in raw_tags] if isinstance(raw_tags, list) else ["distilled"]
                body = f"## Summary\n\n{summary}\n\n## Key Takeaways\n\n" + "\n".join(f"- {p}" for p in points)
                return str(title), str(summary), body, tags
        except json.JSONDecodeError:
            pass

    summary = cleaned[:300]
    return default_title, summary, cleaned, ["distilled"]


class SignalDistiller:
    """Processes pending raw signals into structured knowledge notes."""

    def __init__(
        self,
        store: HybridMemoryPort,
        llm_provider: LLMProviderPort,
        notes_dir: Path | str = "data/notes",
        embedder: EmbedderPort | None = None,
        resource_manager: ResourceManagerPort | None = None,
    ) -> None:
        self.store = store
        self.llm_provider = llm_provider
        self.notes_dir = Path(notes_dir)
        self.embedder = embedder
        self.resource_manager = resource_manager

    def _write_physical_note(self, note: KnowledgeNote, date_str: str, slug: str) -> None:
        """Write note markdown file with YAML frontmatter to notes directory."""
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        primary_file = self.notes_dir / f"{date_str}_{slug}.md"
        if primary_file.exists():
            file_path = primary_file
        else:
            file_path = determine_unique_path(self.notes_dir, slug, date_str)
        text = format_markdown_note(note.title, note.content, note.tags, note.sources, date_str)
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
        slug = slugify(title)
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
        vec = (
            await asyncio.to_thread(self.embedder.embed_query, f"{title}\n{body}")
            if self.embedder
            else None
        )
        await self.store.save_knowledge_note(note, embedding=vec)
        await asyncio.to_thread(self._write_physical_note, note, date_str, slug)
        return note

    async def distill_signal(self, signal: RawSignal) -> KnowledgeNote:
        """Run LLM inference with VRAM confinement and save distilled note."""
        prompt = _build_distill_prompt(signal)
        messages = [Message(role="user", content=prompt)]
        if self.resource_manager is not None and hasattr(self.resource_manager, "inject_unload_vram"):
            call_kwargs = self.resource_manager.inject_unload_vram()
        else:
            call_kwargs = {"extra_body": {"keep_alive": 0}}

        try:
            response = await self.llm_provider.generate(messages, **call_kwargs)
        except Exception as exc:
            raise DistillationError(f"LLM generation failed during distillation of '{signal.id}': {exc}") from exc

        title, summary, body, tags = _parse_distillation(response.content, signal.title)
        return await self._persist_note(signal, title, summary, body, tags)

    async def distill_raw_content(
        self,
        raw_content: str,
        title: str = "Untitled Document",
        source_id: str = "text_input",
        url: str | None = None,
    ) -> KnowledgeNote:
        """Convenience method to distill raw in-memory content directly into a knowledge note."""
        cleaned = raw_content.strip()
        if not cleaned:
            raise DistillationError("Cannot distill empty content")
        stable_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:12]
        signal = RawSignal(
            id=f"text_{stable_hash}",
            source_id=source_id,
            title=title,
            url=url,
            raw_content=cleaned,
            clean_content=cleaned,
        )
        return await self.distill_signal(signal)

    async def distill_file(self, file_path: Path | str) -> KnowledgeNote:
        """Extract text from physical file and distill into a knowledge note."""
        extracted_text, title = extract_text_from_file(file_path)
        return await self.distill_raw_content(
            raw_content=extracted_text,
            title=title,
            source_id="local_file",
            url=str(file_path),
        )

    async def _distill_single_signal(self, signal: RawSignal) -> KnowledgeNote:
        """Backward-compatible proxy to distill_signal."""
        return await self.distill_signal(signal)

    async def distill_batch(self, batch_size: int = 5) -> int:
        """Fetch pending signals, distill them, and transition states."""
        signals = await self.store.get_pending_signals(limit=batch_size)
        if not signals:
            return 0

        success_count = 0
        for signal in signals:
            try:
                await self.distill_signal(signal)
                await self.store.mark_signal_status(signal.id, "processed")
                success_count += 1
                logger.info("Signal '%s' distilled successfully into note.", signal.id)
            except Exception as exc:
                logger.error("Failed to distill signal '%s': %s", signal.id, exc)
                await self.store.mark_signal_status(signal.id, "failed")

        return success_count
