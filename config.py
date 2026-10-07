"""Configuration centrale du système Ekko.

Ce module centralise tous les paramètres de configuration via Pydantic Settings
conformément aux principes de la méthodologie 12-Factor App.
"""

from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Paramètres applicatifs chargés depuis l'environnement et le fichier .env."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Fournisseur LLM ('gemini' ou 'local')
    llm_provider: str = Field(default="local", description="Provider LLM actif")
    gemini_api_key: str = Field(default="", description="Clé d'API Google Gemini")
    gemini_model: str = Field(default="gemini-2.5-flash", description="Nom du modèle Gemini")

    # Configuration modèle local (Ollama / vLLM)
    local_llm_url: str = Field(
        default="http://localhost:11434/v1",
        description="URL de l'API locale compatible OpenAI",
    )
    local_llm_model: str = Field(
        default="qwen2.5:7b",
        description="Identifiant du modèle local",
    )

    # Rétention d'historique (jours)
    history_retention_days: int = Field(
        default=30,
        description="Nombre de jours de conservation de l'historique en base SQLite",
    )

    # Chemins pour la mémoire centrale d'Ekko
    memory_dir_path: Path = Field(
        default=BASE_DIR / "data" / "memory",
        description="Dossier de stockage de la mémoire d'Ekko",
    )
    db_path: Path = Field(
        default=BASE_DIR / "data" / "memory" / "ekko.db",
        description="Base de données SQLite centrale",
    )
    log_dir_path: Path = Field(
        default=BASE_DIR / "data" / "logs",
        description="Dossier de stockage des journaux techniques",
    )

    @field_validator(
        "memory_dir_path",
        "db_path",
        "log_dir_path",
        mode="after",
    )
    @classmethod
    def resolve_path(cls, value: Path) -> Path:
        """Résout automatiquement les chemins relatifs par rapport à la racine du projet."""
        expanded = value.expanduser()
        return (BASE_DIR / expanded).resolve() if not expanded.is_absolute() else expanded.resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retourne l'instance unique mise en cache des paramètres de configuration."""
    return Settings()
