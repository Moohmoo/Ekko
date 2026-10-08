"""Moteur de contexte unifié pour Ekko (Pattern ExecutionContext).

Agrège l'environnement déterministe (horodatage, OS, système),
le profil utilisateur et la mémoire de travail de la session active.
"""

from datetime import datetime
import os
from pathlib import Path
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


class UserProfileContext(BaseModel):
    """Contexte typé du profil utilisateur et de ses préférences."""

    raw_content: str = Field(default="", description="Contenu markdown complet du profil")

    def __str__(self) -> str:
        return self.raw_content


class WorkingMemoryContext(BaseModel):
    """Mémoire de travail typée de la session active."""

    session_id: str = Field(default="default", description="Identifiant unique de session")
    messages: list[dict[str, str]] = Field(default_factory=list, description="Messages récents")
    history_block: str = Field(default="", description="Historique formaté prêt pour l'injection")

    def __str__(self) -> str:
        return self.history_block


class ExecutionContext(BaseModel):
    """Contexte d'exécution global immuable passé à tous les composants."""

    env: EnvironmentContext
    user: UserProfileContext = Field(default_factory=UserProfileContext)
    memory: WorkingMemoryContext = Field(default_factory=WorkingMemoryContext)
    user_profile: str = Field(default="")
    history_block: str = Field(default="")
    session_id: str = Field(default="default")

    def model_post_init(self, __context: object) -> None:
        """Synchronise les représentations riches et les accès plats."""
        if self.user_profile and not self.user.raw_content:
            self.user = UserProfileContext(raw_content=self.user_profile)
        elif self.user.raw_content and not self.user_profile:
            self.user_profile = self.user.raw_content

        if self.history_block and not self.memory.history_block:
            self.memory = WorkingMemoryContext(
                session_id=self.session_id,
                history_block=self.history_block,
            )
        elif self.memory.history_block and not self.history_block:
            self.history_block = self.memory.history_block
            self.session_id = self.memory.session_id

    @property
    def current_year(self) -> int:
        """Raccourci vers l'année courante."""
        return self.env.current_year

    @property
    def current_date(self) -> str:
        """Raccourci vers la date courante."""
        return self.env.current_date


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
        os_name=os.name,
        cwd=str(Path.cwd()),
    )
    recent_messages = storage.get_recent_messages(session_id, limit=history_limit)
    history_str = format_history_block(recent_messages)

    user_ctx = UserProfileContext(raw_content=user_profile)
    mem_ctx = WorkingMemoryContext(
        session_id=session_id,
        messages=recent_messages,
        history_block=history_str,
    )

    return ExecutionContext(
        env=env,
        user=user_ctx,
        memory=mem_ctx,
        user_profile=user_profile,
        history_block=history_str,
        session_id=session_id,
    )
