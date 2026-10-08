"""Moteur de contexte unifié pour Ekko (Pattern ExecutionContext).

Agrège l'environnement déterministe (horodatage, OS, système),
le profil utilisateur et la mémoire de travail de la session active.
"""

from datetime import datetime
from pathlib import Path
import platform
from pydantic import BaseModel, Field
from .storage import SessionStorage
from .prompts import format_history_block


class EnvironmentContext(BaseModel):
    """Contexte d'environnement déterministe résolu sans appel LLM."""

    current_date: str = Field(description="Date courante lisible (ex: 8 octobre 2026)")
    current_year: int = Field(description="Année civile courante")
    current_time: str = Field(description="Heure courante (HH:MM)")
    os_name: str = Field(default="linux", description="Système d'exploitation hôte")
    cwd: str = Field(default="", description="Répertoire de travail actuel")


class ExecutionContext(BaseModel):
    """Contexte d'exécution global immuable passé à tous les composants."""

    env: EnvironmentContext
    user_profile: str = Field(default="")
    session_id: str = Field(default="default")
    history_block: str = Field(default="")
    messages: list[dict[str, str]] = Field(default_factory=list)

    @property
    def current_year(self) -> int:
        """Raccourci vers l'année courante."""
        return self.env.current_year

    @property
    def current_date(self) -> str:
        """Raccourci vers la date courante."""
        return self.env.current_date


def _get_safe_cwd() -> str:
    """Résout le répertoire de travail actuel avec repli sûr sur le dossier utilisateur."""
    try:
        return str(Path.cwd())
    except Exception:
        return str(Path.home())


def build_execution_context(
    storage: SessionStorage,
    session_id: str,
    user_profile: str,
    history_limit: int = 4,
) -> ExecutionContext:
    """Construit instantanément (0 ms) l'ExecutionContext immuable pour un tour de dialogue."""
    now = datetime.now()
    env = EnvironmentContext(
        current_date=now.strftime("%d %B %Y"),
        current_year=now.year,
        current_time=now.strftime("%H:%M"),
        os_name=platform.system(),
        cwd=_get_safe_cwd(),
    )
    recent_messages = storage.get_recent_messages(session_id, limit=history_limit)
    history_str = format_history_block(recent_messages)

    return ExecutionContext(
        env=env,
        user_profile=user_profile,
        session_id=session_id,
        history_block=history_str,
        messages=recent_messages,
    )
