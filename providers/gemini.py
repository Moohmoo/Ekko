"""Implémentation du fournisseur LLM via le SDK officiel Google GenAI.

Exploite les fonctionnalités natives de Structured Output de Gemini
pour garantir des retours conformes aux schémas Pydantic.
"""

from typing import TypeVar
from google import genai
from google.genai import types
from pydantic import BaseModel

from .base import LLMProvider

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """Fournisseur exploitant les modèles Gemini via l'API Google GenAI."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash") -> None:
        """Initialise le client asynchrone Google GenAI avec la clé fournie."""
        if not api_key:
            raise ValueError("Une clé GEMINI_API_KEY valide est requise pour GeminiProvider.")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_instruction: str = "",
    ) -> T:
        """Produit une instance Pydantic validée à partir de la réponse Gemini."""
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            system_instruction=system_instruction or None,
            temperature=0.2,
        )
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        if hasattr(response, "parsed") and isinstance(response.parsed, schema):
            return response.parsed
        return schema.model_validate_json(response.text or "{}")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> str:
        """Produit une réponse textuelle brute (ex: Markdown)."""
        config = types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            temperature=0.3,
        )
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        return (response.text or "").strip()
