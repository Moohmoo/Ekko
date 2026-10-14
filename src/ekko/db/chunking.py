"""Semantic markdown chunking respecting hierarchical document structure."""

import re


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences based on punctuation."""
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _chunk_oversized_paragraph(para: str, max_chars: int, overlap_chars: int) -> list[str]:
    """Split a single paragraph exceeding max_chars into overlapping sentence chunks."""
    sentences = _split_into_sentences(para)
    if not sentences:
        return [para] if para.strip() else []

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_len = 0

    for s in sentences:
        if len(s) > max_chars:
            if current_sentences:
                chunks.append(" ".join(current_sentences))
                current_sentences = []
                current_len = 0
            start = 0
            while start < len(s):
                end = min(start + max_chars, len(s))
                chunks.append(s[start:end])
                if end == len(s):
                    break
                step = end - overlap_chars
                start = step if step > start else end
            continue

        additional_len = len(s) + (1 if current_sentences else 0)
        if current_len + additional_len <= max_chars:
            current_sentences.append(s)
            current_len += additional_len
        else:
            if current_sentences:
                chunks.append(" ".join(current_sentences))
                overlap_acc: list[str] = []
                overlap_len = 0
                for prev_s in reversed(current_sentences):
                    cost = len(prev_s) + (1 if overlap_acc else 0)
                    if overlap_len + cost <= overlap_chars:
                        overlap_acc.insert(0, prev_s)
                        overlap_len += cost
                    else:
                        break
                current_sentences = overlap_acc + [s]
                current_len = sum(len(x) for x in current_sentences) + max(0, len(current_sentences) - 1)
            else:
                current_sentences = [s]
                current_len = len(s)

    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return [c.strip() for c in chunks if c.strip()]


def _chunk_section(section: str, max_chars: int, overlap_chars: int) -> list[str]:
    """Split a section exceeding max_chars into paragraph-based chunks."""
    paragraphs = [p.strip() for p in section.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current_paras: list[str] = []
    current_len = 0

    for para in paragraphs:
        if len(para) > max_chars:
            if current_paras:
                chunks.append("\n\n".join(current_paras))
                current_paras = []
                current_len = 0
            sub_chunks = _chunk_oversized_paragraph(para, max_chars, overlap_chars)
            chunks.extend(sub_chunks)
            continue

        additional_len = len(para) + (2 if current_paras else 0)
        if current_len + additional_len <= max_chars:
            current_paras.append(para)
            current_len += additional_len
        else:
            if current_paras:
                chunks.append("\n\n".join(current_paras))
            current_paras = [para]
            current_len = len(para)

    if current_paras:
        chunks.append("\n\n".join(current_paras))

    return [c.strip() for c in chunks if c.strip()]


def chunk_markdown(text: str, max_chars: int = 1500, overlap_chars: int = 200) -> list[str]:
    """Chunk Markdown document hierarchically by headings, paragraphs, and sentences.

    Short documents (<= max_chars) are returned as a single chunk immediately.
    """
    cleaned = text.strip()
    if not cleaned:
        return []

    if len(cleaned) <= max_chars:
        return [cleaned]

    # Split on markdown headings #, ##, ###
    sections = [s.strip() for s in re.split(r"(?=(?:^|\n)#{1,3}\s)", cleaned) if s.strip()]
    if not sections:
        sections = [cleaned]

    chunks: list[str] = []
    current_acc: list[str] = []
    current_acc_len = 0

    for sec in sections:
        if len(sec) > max_chars:
            if current_acc:
                chunks.append("\n\n".join(current_acc))
                current_acc = []
                current_acc_len = 0
            sub_chunks = _chunk_section(sec, max_chars, overlap_chars)
            chunks.extend(sub_chunks)
        else:
            additional_len = len(sec) + (2 if current_acc else 0)
            if current_acc_len + additional_len <= max_chars:
                current_acc.append(sec)
                current_acc_len += additional_len
            else:
                if current_acc:
                    chunks.append("\n\n".join(current_acc))
                current_acc = [sec]
                current_acc_len = len(sec)

    if current_acc:
        chunks.append("\n\n".join(current_acc))

    return [c.strip() for c in chunks if c.strip()]
