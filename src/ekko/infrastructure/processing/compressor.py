"""Heuristic text compression, token budgeting, and chunking pipeline."""

from enum import Enum
import re

TRUNCATION_NOTICE = "\n\n[... Contenu tronqué pour respecter le budget de tokens ...]"

# Patterns identifying sections to prune
NOISY_SECTION_HEADERS = [
    r"^#{1,6}\s*(?:references?|bibliograph(?:y|ie)|notes?|footnotes?|sources?)\b",
    r"^#{1,6}\s*(?:see also|voir aussi|external links?|liens externes?)\b",
    r"^#{1,6}\s*(?:about the authors?|à propos de l['’]auteur)\b",
]

# Patterns identifying single-line UI / legal boilerplate
BOILERPLATE_PATTERNS = [
    r"(?i)\bcookie\s+policy\b",
    r"(?i)\bprivacy\s+policy\b",
    r"(?i)\bterms\s+of\s+service\b",
    r"(?i)\ball\s+rights\s+reserved\b",
    r"(?i)^navigation\s*\|",
    r"(?i)^\s*\|\s*home\s*\|",
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
    return any(re.search(pat, stripped) for pat in BOILERPLATE_PATTERNS)


def _split_into_paragraphs(text: str) -> list[str]:
    """Split text into raw paragraphs, filtering out empty ones."""
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


class ContentCompressor:
    """Compresses raw text via heuristic pruning, token budgeting, and chunking."""

    def calculate_budget(self, profile: ModelProfile | str = ModelProfile.STANDARD) -> int:
        """Return the maximum token budget for the given model profile."""
        key = ModelProfile(profile) if isinstance(profile, str) else profile
        return PROFILE_TOKEN_BUDGETS.get(key, 8192)

    def prune_heuristics(self, text: str) -> str:
        """Strip boilerplate lines and trailing references from markdown content."""
        lines = text.splitlines()
        retained_lines: list[str] = []

        for line in lines:
            # Stop accumulating if we encounter reference/bibliography section header
            if any(re.search(pat, line.strip(), re.IGNORECASE) for pat in NOISY_SECTION_HEADERS):
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
    ) -> str:
        """Truncate text if it exceeds the character limit for the target profile."""
        max_chars = self.calculate_budget(profile) * chars_per_token
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rstrip() + TRUNCATION_NOTICE

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
                # Keep tail paragraph for overlap if possible
                overlap_p = current[-1] if len(current[-1]) <= overlap_chars else ""
                current = [overlap_p, p] if overlap_p else [p]
                current_len = sum(len(x) + 2 for x in current)
            else:
                current.append(p)
                current_len += p_len + 2

        if current:
            chunks.append("\n\n".join(current).strip())

        return chunks
