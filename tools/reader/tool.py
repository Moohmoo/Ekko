"""Outil d'extraction et de lecture du contenu textuel d'une page web (Universal Reader).

Permet à Ekko de consulter un article, une documentation ou un README GitHub en profondeur
à partir d'une URL trouvée lors d'une recherche.
"""

import re
import httpx
from pydantic import BaseModel, Field
from tools.base import BaseTool

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"


class ReaderParams(BaseModel):
    """Paramètres pour la lecture d'une page web ou d'un document en ligne."""

    url: str = Field(description="URL complète de la page web, de l'article ou du README à lire.")
    max_chars: int = Field(default=4000, description="Nombre maximum de caractères à extraire (défaut: 4000).")


def _clean_html_to_text(html_content: str) -> str:
    """Élimine balises, scripts et styles pour extraire le texte brut épuré."""
    no_script = re.sub(r"<(script|style|nav|footer|header)[^>]*>[\s\S]*?</\1>", " ", html_content, flags=re.I)
    no_tags = re.sub(r"<[^>]+>", " ", no_script)
    return " ".join(no_tags.split())


class ReaderTool(BaseTool):
    """Outil universel permettant d'extraire et lire le contenu textuel d'une URL."""

    name = "reader"
    description = (
        "Télécharge et extrait le texte pur d'une URL (page web, article, documentation, README GitHub). "
        "À utiliser pour analyser en détail une source découverte lors d'une recherche."
    )
    parameters_schema = ReaderParams

    async def execute(self, url: str, max_chars: int = 4000) -> str:
        """Télécharge la page de manière asynchrone et extrait le texte utile."""
        clean_url = url.strip()
        if not clean_url.startswith(("http://", "https://")):
            clean_url = f"https://{clean_url}"
        headers = {"User-Agent": USER_AGENT}
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(clean_url, headers=headers)
                resp.raise_for_status()
                ctype = resp.headers.get("content-type", "").lower()
                if ctype and not any(t in ctype for t in ("text", "html", "json", "xml", "markdown")):
                    return f"Le document `{clean_url}` n'est pas un format textuel lisible ({ctype})."
                if len(resp.content) > 2 * 1024 * 1024:
                    return f"Le document `{clean_url}` dépasse la taille maximale autorisée (2 Mo)."
                text = _clean_html_to_text(resp.text)
                truncated = text[:max_chars] + ("..." if len(text) > max_chars else "")
                return f"Contenu extrait de `{clean_url}` :\n\n{truncated}"
        except Exception as exc:
            return f"Impossible de charger la page `{clean_url}` : {exc}"
