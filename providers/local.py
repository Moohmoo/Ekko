"""Fournisseur LLM pour modèles locaux compatibles avec l'API OpenAI.

Permet d'utiliser des modèles hébergés sur Ollama, vLLM ou LM Studio
sans dépendre d'une connexion internet ni de quotas d'API tiers.
"""

import json
import re
from typing import Any, TypeVar
import httpx
from pydantic import BaseModel

from .base import LLMProvider

T = TypeVar("T", bound=BaseModel)


def clean_json_payload(text: str) -> str:
    """Extrait le JSON brut si le modèle l'a enveloppé dans des balises Markdown."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text.strip()


class LocalProvider(LLMProvider):
    """Fournisseur interrogeant une instance locale (ex: Ollama / vLLM)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model_name: str = "llama3.1",
    ) -> None:
        """Initialise l'URL de base et le modèle local cible."""
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    async def _post_chat(self, payload: dict[str, Any]) -> str:
        """Envoie une requête POST vers le point de terminaison chat/completions."""
        url = f"{self.base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            return str(data["choices"][0]["message"]["content"])

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_instruction: str = "",
    ) -> T:
        """Génère et désérialise un résultat structuré depuis le modèle local."""
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        full_system = (
            f"{system_instruction}\n"
            f"Tu dois impérativement répondre uniquement avec un JSON valide respectant ce schéma :\n"
            f"{schema_json}"
        )
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": full_system},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        raw_text = await self._post_chat(payload)
        cleaned = clean_json_payload(raw_text)
        return schema.model_validate_json(cleaned)

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> str:
        """Génère du texte libre (Markdown) depuis le modèle local."""
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        return (await self._post_chat(payload)).strip()
