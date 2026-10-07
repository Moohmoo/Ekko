"""Implémentation du fournisseur LLM via le SDK officiel Google GenAI.

Exploite les fonctionnalités natives de Structured Output de Gemini avec
options HTTP explicites (X-Server-Timeout), retry automatique et logs de diagnostic.
"""

import asyncio
import logging
import time
from typing import Any, TypeVar
from google import genai
from google.genai import types
from pydantic import BaseModel

from .base import LLMProvider

logger = logging.getLogger("ekko.providers.gemini")
T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """Fournisseur exploitant les modèles Gemini via l'API Google GenAI."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        timeout: float = 12.0,
    ) -> None:
        """Initialise le client Google GenAI avec timeout et options de serveur."""
        if not api_key:
            raise ValueError("Une clé GEMINI_API_KEY valide est requise pour GeminiProvider.")
        timeout_ms = int(timeout * 1000)
        options = types.HttpOptions(timeout=timeout_ms)
        self.client = genai.Client(api_key=api_key, http_options=options)
        self.model_name = model_name
        self.timeout = timeout

    async def _call_api_with_retry(
        self, prompt: str, config: types.GenerateContentConfig, max_retries: int = 2
    ) -> Any:
        """Exécute l'appel distant avec timeout strict et tentative de secours."""
        for attempt in range(1, max_retries + 1):
            t0 = time.perf_counter()
            logger.debug("Appel Gemini [%s] (tentative %d/%d)", self.model_name, attempt, max_retries)
            try:
                res = await asyncio.wait_for(
                    self.client.aio.models.generate_content(
                        model=self.model_name, contents=prompt, config=config
                    ),
                    timeout=self.timeout,
                )
                logger.debug("Réponse Gemini reçue en %.2fs", time.perf_counter() - t0)
                return res
            except Exception as exc:
                elapsed = time.perf_counter() - t0
                logger.warning("Échec tentative %d/%d (%.2fs): %s", attempt, max_retries, elapsed, exc)
                if attempt == max_retries:
                    raise TimeoutError(f"Le serveur Gemini n'a pas répondu après {max_retries} essais.") from exc
                await asyncio.sleep(0.5)

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
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0.2,
        )
        response = await self._call_api_with_retry(prompt, config)
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
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0.3,
        )
        response = await self._call_api_with_retry(prompt, config)
        return (response.text or "").strip()
