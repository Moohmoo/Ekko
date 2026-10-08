"""Agent Validateur et Critique de conformité pour Ekko (Evaluator / Checker).

Garantit la rigueur scientifique et technique des réponses en élaguant
le bruit marketing, les spéculations et les hallucinations non sourcées.
"""

from providers.base import LLMProvider

VALIDATOR_SYSTEM_PROMPT = """Tu es le Validateur Critique d'Ekko, un filtre d'ingénierie et de rigueur scientifique pour un ingénieur en informatique et bioinformatique.

### PROFIL UTILISATEUR :
{user_profile}

### MISSION CRITIQUE :
Tu analyses le projet de réponse préparé par l'agent enquêteur au regard des observations d'outils collectées et de la question utilisateur.

### SOURCES DE RÉFÉRENCE :
Les articles scientifiques (arXiv), dépôts de code (GitHub) et documentations techniques présents dans les observations sont des sources primaires vérifiées de référence.

### DIRECTIVES DE VALIDATION STRICTES :
1. ZÉRO BRUIT MARKETING : Élimine impitoyablement tout battage médiatique, article sponsorisé ou texte commercial sans substance technique.
2. VALORISATION DES SOURCES PRIMAIRES : Conserve et synthétise tous les faits solides étayés par les observations. Obligation stricte de préserver les liens Markdown [Titre](URL) d'origine dans chaque puce. Ne supprime jamais les URLs.
3. STRUCTURE DE REVUE SCIENTIFIQUE : Pour toute recherche ou veille technique, structure la restitution ainsi :
   - Contexte / Problème résolu
   - Méthode / Architecture
   - Résultats ou Dépôt vérifié
   - Limites éventuelles
4. ABSENCE DE SOURCES : Uniquement si les observations sont vides ou composées exclusivement de spam promotionnel, réponds :
   "Aucune source technique fiable n'a été trouvée sur ce sujet récemment."
5. STYLE DIRECT : Va directement au résultat épuré sans AUCUN bavardage d'introduction (interdiction de phrases comme 'Voici la version...')."""


def _has_primary_sources(observations: list[str]) -> bool:
    """Détecte la présence de sources scientifiques ou techniques fiables dans les observations."""
    obs_text = " ".join(observations).lower()
    return any(marker in obs_text for marker in ("arxiv.org", "github.com", "doi.org"))


def format_validation_prompt(
    user_query: str,
    draft_answer: str,
    observations: list[str],
) -> str:
    """Met en forme le prompt de validation avec le projet de réponse et les preuves d'outils."""
    obs_block = "\n".join(observations) if observations else "Aucune observation d'outil (réponse directe)."
    return (
        f"Demande initiale de l'utilisateur : {user_query}\n\n"
        f"Observations des outils collectées :\n{obs_block}\n\n"
        f"Projet de réponse à critiquer et valider :\n{draft_answer}\n\n"
        "Consigne : Reformule la version finale validée, épurée de tout bruit et rigoureusement étayée."
    )


async def validate_draft(
    provider: LLMProvider,
    user_query: str,
    draft_answer: str,
    observations: list[str],
    user_profile: str,
) -> str:
    """Critique, épure et certifie le brouillon final produit par l'enquêteur ReAct."""
    if not observations and len(draft_answer.strip().split()) < 25:
        return draft_answer

    system_instruction = VALIDATOR_SYSTEM_PROMPT.replace("{user_profile}", user_profile)
    prompt = format_validation_prompt(user_query, draft_answer, observations)
    validated = (await provider.generate_text(
        prompt=prompt,
        system_instruction=system_instruction,
    )).strip()

    if not validated:
        return draft_answer
    if _has_primary_sources(observations) and "aucune source" in validated.lower():
        return draft_answer
    return validated
