"""Shared formatting, slugification, and markdown persistence utilities for notes."""

from pathlib import Path
import re
import unicodedata


def slugify(text: str) -> str:
    """Normalize text into an alphanumeric filesystem-safe slug."""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[/\\.]+", "-", normalized)
    normalized = re.sub(r"[^\w\s-]", "", normalized.lower())
    normalized = re.sub(r"[-\s]+", "-", normalized).strip("-")
    return normalized if normalized else "note"


def format_markdown_note(
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

    lines.extend(["---", "", f"# {title}", "", content.strip(), ""])
    return "\n".join(lines)


def determine_unique_path(base_dir: Path, slug: str, date_str: str) -> Path:
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
