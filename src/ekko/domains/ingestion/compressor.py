"""Heuristic text compression, token budgeting, and chunking pipeline."""

from enum import Enum
import re

TRUNCATION_NOTICE = "\n\n[... Content truncated to match token budget ...]"

# Precompiled patterns identifying sections to prune
NOISY_SECTION_HEADERS = [
    re.compile(r"^#{1,6}\s*(?:references?|bibliograph(?:y|ie)|footnotes?|sources?)\b", re.IGNORECASE),
    re.compile(r"^#{1,6}\s*(?:see also|voir aussi|external links?|liens externes?)\b", re.IGNORECASE),
    re.compile(r"^#{1,6}\s*(?:about the authors?|à propos de l['’]auteur)\b", re.IGNORECASE),
]

# Precompiled patterns identifying single-line UI / legal boilerplate
BOILERPLATE_PATTERNS = [
    re.compile(r"\bcookie\s+policy\b", re.IGNORECASE),
    re.compile(r"\bprivacy\s+policy\b", re.IGNORECASE),
    re.compile(r"\bterms\s+of\s+service\b", re.IGNORECASE),
    re.compile(r"\ball\s+rights\s+reserved\b", re.IGNORECASE),
    re.compile(r"^navigation\s*\|", re.IGNORECASE),
    re.compile(r"^\s*\|\s*home\s*\|", re.IGNORECASE),
]


class ModelProfile(str, Enum):
    """Inference profiles for Bring-Your-Own-Model (BYOM) token budgeting."""

    MICRO = "Micro"
    STANDARD = "Standard"
    LARGE = "Large"


PROFILE_TOKEN_BUDGETS: dict[ModelProfile, int] = {
    ModelProfile.MICRO: 2048,
    ModelProfile.STANDARD: 8192,
    ModelProfile.LARGE: 32768,
}


def _is_boilerplate_line(line: str) -> bool:
    """Check if a line matches known noise or cookie/legal banners."""
    stripped = line.strip()
    return any(pat.search(stripped) for pat in BOILERPLATE_PATTERNS)


def _split_into_paragraphs(text: str) -> list[str]:
    """Split text into raw paragraphs, filtering out empty ones."""
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


class ContentCompressor:
    """Compresses raw text via heuristic pruning, token budgeting, and chunking."""

    def calculate_budget(
        self,
        profile: ModelProfile | str = ModelProfile.STANDARD,
        custom_budget: int | None = None,
    ) -> int:
        """Return the token budget for the profile or explicit custom budget."""
        if custom_budget is not None and custom_budget > 0:
            return custom_budget
        key = ModelProfile(profile) if isinstance(profile, str) else profile
        return PROFILE_TOKEN_BUDGETS.get(key, 8192)

    def prune_heuristics(self, text: str) -> str:
        """Strip boilerplate lines and trailing references from markdown content."""
        lines = text.splitlines()
        retained_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            # Stop accumulating if we encounter reference/bibliography section header
            if any(pat.search(stripped) for pat in NOISY_SECTION_HEADERS):
                break
            if not _is_boilerplate_line(line):
                retained_lines.append(line)

        cleaned = "\n".join(retained_lines)
        return re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    def truncate_to_budget(
        self,
        text: str,
        profile: ModelProfile | str = ModelProfile.STANDARD,
        chars_per_token: int = 4,
        notice: str | None = None,
        custom_budget: int | None = None,
    ) -> str:
        """Truncate text if it exceeds character limit for target profile or custom budget."""
        max_chars = self.calculate_budget(profile, custom_budget=custom_budget) * chars_per_token
        if len(text) <= max_chars:
            return text
        truncation_marker = notice if notice is not None else TRUNCATION_NOTICE
        return text[:max_chars].rstrip() + truncation_marker

    def chunk_text(
        self,
        text: str,
        max_chunk_chars: int = 2000,
        overlap_chars: int = 200,
    ) -> list[str]:
        """Split text into overlapping chunks respecting paragraph boundaries."""
        paragraphs = _split_into_paragraphs(text)
        if not paragraphs:
            return []

        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for p in paragraphs:
            p_len = len(p)
            if current and (current_len + p_len + 2 > max_chunk_chars):
                chunk_str = "\n\n".join(current).strip()
                chunks.append(chunk_str)
                # Keep tail paragraph or tail slice for overlap to guarantee context continuity
                last_p = current[-1]
                if len(last_p) <= overlap_chars:
                    overlap_p = last_p
                else:
                    overlap_p = last_p[-overlap_chars:]
                current = [overlap_p, p] if overlap_p else [p]
                current_len = sum(len(x) + 2 for x in current)
            else:
                current.append(p)
                current_len += p_len + 2

        if current:
            chunks.append("\n\n".join(current).strip())

        return chunks
