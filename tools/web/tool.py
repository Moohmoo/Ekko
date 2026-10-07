"""Outil d'extraction et de lecture du contenu textuel d'une page web.

Permet à Ekko de consulter un article ou une documentation en profondeur
à partir d'une URL trouvée lors d'une recherche.
"""

import re
import httpx
from pydantic import BaseModel, Field
from tools.base import BaseTool

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"


class FetchPageParams(BaseModel):
    """Paramètres pour la lecture d'une page web."""

    url: str = Field(description="URL complète de la page web ou de l'article à lire.")
    max_chars: int = Field(default=3000, description="Nombre maximum de caractères à extraire (défaut: 3000).")


def _clean_html_to_text(html_content: str) -> str:
    """Élimine balises, scripts et styles pour extraire le texte brut épuré."""
    no_script = re.sub(r"<(script|style|nav|footer|header)[^>]*>[\s\S]*?</\1>", " ", html_content, flags=re.I)
    no_tags = re.sub(r"<[^>]+>", " ", no_script)
    return " ".join(no_tags.split())


class FetchPageTool(BaseTool):
    """Outil permettant d'extraire et lire le contenu textuel d'une page web."""

    name = "fetch_page"
    description = (
        "Télécharge et extrait le contenu textuel d'une page web ou d'un article à partir de son URL. "
        "À utiliser pour analyser en détail une source ou un article trouvé sur le web."
    )
    parameters_schema = FetchPageParams

    async def execute(self, url: str, max_chars: int = 3000) -> str:
        """Télécharge la page de manière asynchrone et extrait le texte utile."""
        headers = {"User-Agent": USER_AGENT}
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                text = _clean_html_to_text(resp.text)
                truncated = text[:max_chars] + ("..." if len(text) > max_chars else "")
                return f"Contenu extrait de `{url}` :\n\n{truncated}"
        except Exception as exc:
            return f"Impossible de charger la page `{url}` : {exc}"
