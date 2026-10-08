"""Tests unitaires pour le chargement et l'initialisation du profil utilisateur."""

from pathlib import Path
from agent.user_profile import load_user_profile


def test_load_user_profile_creates_default(tmp_path: Path) -> None:
    """Vérifie la création automatique du profil par défaut si absent."""
    profile_content = load_user_profile(tmp_path)
    assert "Profil Utilisateur" in profile_content
    assert (tmp_path / "user_profile.md").is_file()


def test_load_user_profile_reads_existing(tmp_path: Path) -> None:
    """Vérifie la lecture d'un profil personnalisé existant."""
    custom_file = tmp_path / "user_profile.md"
    custom_file.write_text("Custom user profile content", encoding="utf-8")

    profile_content = load_user_profile(tmp_path)
    assert profile_content == "Custom user profile content"
