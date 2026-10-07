"""Agent 2 : Le Rédacteur (Synthèse et rédaction du briefing en Markdown).

Prend la sélection de l'Agent 1 et produit une synthèse journalistique concise,
directe et percutante au format Markdown strict sans bavardage.
"""

from watch.models import Article, SelectionResult
from providers import LLMProvider

WRITER_SYSTEM_PROMPT = """Tu es un journaliste technique chevronné et synthétique.
Ton rôle est de rédiger un 'Morning Briefing' Markdown direct à destination d'un ingénieur.
Règles strictes :
- AUCUNE introduction, salutation ni conclusion (pas de 'Bonjour', 'Voici le briefing', etc.).
- Conserve exactement le format Markdown spécifié pour chaque article :

### [Catégorie] Titre de l'article
- **C'est quoi :** Explication concise en 1 phrase claire vulgarisant le sujet.
- **Pourquoi on en parle :** Impact technique direct et intérêt industriel ou académique.
- [Lien](URL)

Sépare chaque article par un saut de ligne. N'altère pas les URLs.
"""


def format_selection_context(
    selection: SelectionResult,
    source_articles: list[Article],
) -> str:
    """Associe les métadonnées et résumés sources aux articles retenus pour enrichir le contexte."""
    article_by_url = {art.url: art for art in source_articles}
    blocks: list[str] = []
    for sel in selection.articles:
        source_art = article_by_url.get(sel.url)
        summary = source_art.summary if source_art else ""
        source_name = source_art.source_name if source_art else "Source"
        blocks.append(
            f"- Titre : {sel.title}\n"
            f"  Catégorie : {sel.category}\n"
            f"  URL : {sel.url}\n"
            f"  Source : {source_name}\n"
            f"  Contexte / Résumé : {summary}\n"
        )
    return "\n".join(blocks)


async def generate_briefing(
    selection: SelectionResult,
    source_articles: list[Article],
    provider: LLMProvider,
) -> str:
    """Génère le texte Markdown complet du briefing du jour à partir de la sélection."""
    if not selection.articles:
        return "# Morning Briefing\n\nAucune actualité majeure retenue aujourd'hui."

    context = format_selection_context(selection, source_articles)
    prompt = (
        "Rédige le briefing Markdown pour les articles sélectionnés suivants. "
        "Respecte scrupuleusement la structure demandée :\n\n"
        f"{context}"
    )
    return await provider.generate_text(
        prompt=prompt,
        system_instruction=WRITER_SYSTEM_PROMPT,
    )
