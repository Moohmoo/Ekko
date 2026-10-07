"""Agent 1 : Le Trieur (Classification et filtrage anti-bruit).

Analyse la liste des articles candidats, élimine le bruit (crypto, patch notes mineurs,
clickbait) et retient les 3 à 5 sujets majeurs pour un ingénieur informatique / bioinformatique.
"""

import json
from providers import LLMProvider
from ..schemas import Article, SelectedArticle, SelectionResult

CLASSIFIER_SYSTEM_PROMPT = """Tu es un filtre expert et exigeant pour un ingénieur informatique et bioinformaticien.
Ton rôle est d'agir comme pare-feu anti-bruit :
- Rejette catégoriquement le clickbait, la crypto, les annonces marketing et les patch notes mineurs.
- Sélectionne uniquement la "crème de la crème" (3 à 5 articles maximum).
- Priorise : lancements majeurs de modèles/architectures, frameworks SOTA, découvertes en bioinformatique/sciences.
- Chaque article sélectionné doit être classé dans l'une des 3 catégories suivantes :
  1. "Tech & IA"
  2. "Data & Backend"
  3. "Sciences & Bio"
- N'invente aucune URL : utilise STRICTEMENT les URLs fournies dans la liste d'entrée.
"""


def format_articles_for_prompt(articles: list[Article]) -> str:
    """Met en forme la liste des articles candidats pour le prompt du classifieur."""
    payload = [
        {
            "index": idx + 1,
            "title": art.title,
            "url": art.url,
            "source": art.source_name,
            "summary": art.summary,
        }
        for idx, art in enumerate(articles)
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def validate_selected_articles(
    result: SelectionResult,
    source_articles: list[Article],
) -> SelectionResult:
    """Filtre les hallucinations d'URLs éventuelles en vérifiant la liste source."""
    valid_urls = {art.url: art for art in source_articles}
    filtered: list[SelectedArticle] = []
    for item in result.articles:
        if item.url in valid_urls:
            filtered.append(item)
    return SelectionResult(articles=filtered[:5])


async def classify_articles(
    articles: list[Article],
    provider: LLMProvider,
) -> SelectionResult:
    """Orchestre le filtrage des articles par l'Agent 1 avec validation post-génération."""
    if not articles:
        return SelectionResult(articles=[])

    prompt = (
        "Voici les articles candidats du jour. Analyse-les et sélectionne les 3 à 5 "
        "articles les plus pertinents selon tes critères d'expertise :\n\n"
        f"{format_articles_for_prompt(articles)}"
    )
    result = await provider.generate_structured(
        prompt=prompt,
        schema=SelectionResult,
        system_instruction=CLASSIFIER_SYSTEM_PROMPT,
    )
    return validate_selected_articles(result, articles)
