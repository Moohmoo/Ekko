"""Gestion et initialisation du profil utilisateur Markdown."""

from pathlib import Path

from .prompts import DEFAULT_PROFILE_CONTENT


def load_user_profile(memory_dir: Path) -> str:
    """Charge le profil Markdown de l'utilisateur ou initialise le gabarit par défaut."""
    profile_path = memory_dir / "user_profile.md"
    if not profile_path.is_file():
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(DEFAULT_PROFILE_CONTENT.strip() + "\n", encoding="utf-8")
    return profile_path.read_text(encoding="utf-8").strip()
