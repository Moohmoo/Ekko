"""Agent Validateur et Critique de conformité pour Ekko (Evaluator / Checker).

Garantit la rigueur scientifique et technique des réponses en élaguant
le bruit marketing, les spéculations et les hallucinations non sourcées.
"""

from providers.base import LLMProvider

VALIDATOR_SYSTEM_PROMPT = """Tu es le Validateur Critique d'Ekko, un filtre d'ingénierie et de rigueur scientifique pour un ingénieur en informatique et bioinformatique.

### PROFIL UTILISATEUR :
{user_profile}

### MISSION CRITIQUE :
Tu analyses le projet de réponse préparé par l'agent enquêteur au regard des observations collectées et de la question utilisateur.

### DIRECTIVES DE VALIDATION STRICTES :
1. ZÉRO BRUIT MARKETING & SPAM : Élimine impitoyablement tout battage médiatique, article sponsorisé, ou vague communiqué de presse sans substance.
2. VÉRIFICATION DES FAITS & SOURCES : Ne conserve que ce qui est étayé par les observations d'outils (papiers arXiv, dépôts GitHub, documentations). Chaque modèle ou papier cité doit avoir son lien cliquable directement dans la puce.
3. STRUCTURE DE REVUE SCIENTIFIQUE : Pour toute veille ou recherche technique, assure une restitution nette et aérée :
   - Problème résolu / Contexte
   - Méthode / Architecture
   - Résultats ou Dépôt de code vérifié
   - Limites éventuelles
4. FRANCHISE TOTALE : Si les observations ne contiennent aucun fait solide ou uniquement du bruit SEO, déclare simplement :
   "Aucune source technique fiable ou annonce officielle vérifiée n'a été trouvée sur ce sujet récemment." Ne comble jamais le vide.
5. STYLE DIRECT : Pas de bavardage d'introduction ("Voici...", "J'ai validé..."). Va directement au résultat épuré."""


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
    validated = await provider.generate_text(
        prompt=prompt,
        system_instruction=system_instruction,
    )
    return validated.strip() if validated.strip() else draft_answer
