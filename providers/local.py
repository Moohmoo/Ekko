"""Fournisseur LLM pour modèles locaux compatibles avec l'API OpenAI.

Permet d'utiliser des modèles hébergés sur Ollama, vLLM ou LM Studio
sans dépendre d'une connexion internet ni de quotas d'API tiers.
"""

from collections.abc import AsyncIterator
import json
import re
from typing import Any, TypeVar
import httpx
from pydantic import BaseModel

from .base import LLMProvider

T = TypeVar("T", bound=BaseModel)


def _unwrap_schema_fragments(obj: Any) -> Any:
    """Recursively unwraps JSON schema fragments echoed by compact models."""
    if isinstance(obj, dict):
        if "properties" in obj and isinstance(obj["properties"], dict):
            return _unwrap_schema_fragments(obj["properties"])
        if ("anyOf" in obj or "type" in obj) and "default" in obj:
            return _unwrap_schema_fragments(obj["default"])
        if "default" in obj and len(obj) <= 4:
            return _unwrap_schema_fragments(obj["default"])
        if "value" in obj and len(obj) <= 3:
            return _unwrap_schema_fragments(obj["value"])
        return {k: _unwrap_schema_fragments(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_unwrap_schema_fragments(item) for item in obj]
    return obj


def clean_json_payload(text: str) -> str:
    """Extracts raw JSON and strips out schema metadata wrappers."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    cleaned = match.group(1).strip() if match else text.strip()
    try:
        data = json.loads(cleaned)
        unwrapped = _unwrap_schema_fragments(data)
        return json.dumps(unwrapped)
    except Exception:
        pass
    return cleaned


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

    async def stream_text(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> AsyncIterator[str]:
        """Génère du texte en flux continu (SSE) depuis le serveur local Ollama/vLLM."""
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "stream": True,
        }
        url = f"{self.base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and not line.strip().endswith("[DONE]"):
                        try:
                            data = json.loads(line[6:].strip())
                            delta = data["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            continue
