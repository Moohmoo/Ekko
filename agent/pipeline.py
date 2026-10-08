"""Pipeline de recherche documentaire et revue scientifique pour Ekko.

Implémente le workflow déterministe en 3 étapes spécialisées :
Cadrage & Expansion de requêtes -> Collecte & Dédoublonnage -> Synthèse certifiée.
"""

import asyncio
from collections.abc import AsyncIterator
import time
from typing import Any
from providers.base import LLMProvider
from tools.search.tool import SearchTool
from .schemas import SearchPlan

ROUTER_SYSTEM_PROMPT = """Tu es l'Architecte de Recherche d'Ekko pour un ingénieur en informatique et bioinformatique.

### MISSION :
Analyse la demande utilisateur et formule le plan de recherche adapté.

### RÈGLES STRICTES :
1. DEMANDE DIRECTE SANS OUTIL (is_search_needed=False) :
   - Salutation, remerciement ou question théorique connue sans besoin de recherche externe.
   -> Renseigne 'direct_answer' sobrement et laisse 'queries' vide ([]).
2. RECHERCHE TECHNIQUE / SOTA / CODE / DOC (is_search_needed=True) :
   - Littérature scientifique, modèles récents, bioinformatique -> focus='academic'.
     Exemple : 'repliement ARN' -> queries=['RNA structure folding deep learning', 'RNA inverse design']
   - Dépôts GitHub, code source, implémentations -> focus='code'.
     Exemple : 'framework vLLM' -> queries=['vllm project', 'vllm inference']
   - Documentation technique, veille technologique, actualités tech -> focus='web'.
     Exemple : 'dernières avancées tech' -> queries=['latest tech advancements', 'breakthrough technology innovations']
   -> OBLIGATION : Tu DOIS obligatoirement renseigner 'queries' avec 1 ou 2 requêtes clés en ANGLAIS.
   -> Traduis fidèlement les concepts métiers sans mots de remplissage parasites.
3. INDÉPENDANCE DE LA DEMANDE :
   Chaque question doit être traitée selon son thème propre sans forcer le sujet précédent."""

SYNTHESIZER_SYSTEM_PROMPT = """Tu es le Rédacteur Scientifique et Technique d'Ekko pour un ingénieur en bioinformatique et IA.

### PROFIL :
{user_profile}

### MISSION :
Rédige une synthèse technique rigoureuse à partir des sources documentaires fournies.

### DIRECTIVES DE RÉDACTION :
1. STRUCTURE DE REVUE SCIENTIFIQUE :
   - **Contexte & Verrou :** Problème adressé et enjeu scientifique.
   - **Méthode & Architecture :** Approches, architectures et modèles employés.
   - **Résultats & Code :** Avancées démontrées avec LIENS CLIQUABLES OBLIGATOIRES.
   - **Limites :** Verrous restants ou contraintes méthodologiques.
2. CONSERVATION DES LIENS MARKDOWN :
   Chaque article ou dépôt cité DOIT comporter son lien cliquable :
   - **[Nom ou Titre](URL)** (Auteurs/Date) : faits concrets.
   Interdiction formelle de supprimer les URLs présentes dans les sources.
3. STYLE DIRECT : Va immédiatement au résultat épuré sans bavardage d'introduction ni récitation de règles en conclusion.
4. ABSENCE DE SOURCES : Uniquement si les sources fournies sont totalement vides, indique qu'aucune source technique n'a été trouvée."""


async def plan_research(
    provider: LLMProvider,
    query: str,
    history_context: str = "",
) -> SearchPlan:
    """Cadre l'intention et génère les requêtes de recherche ciblées en anglais."""
    prompt = f"Demande utilisateur : {query}"
    if history_context:
        prompt = f"{history_context}\n\n{prompt}"
    plan = await provider.generate_structured(
        prompt=prompt,
        schema=SearchPlan,
        system_instruction=ROUTER_SYSTEM_PROMPT,
    )
    if plan.is_search_needed and not plan.queries:
        plan.queries = [query.strip()]
    return plan


async def collect_sources(
    search_tool: SearchTool,
    plan: SearchPlan,
) -> tuple[str, int, float]:
    """Interroge les moteurs de recherche en parallèle et dédoublonne les observations."""
    t0 = time.perf_counter()
    queries = plan.queries[:2] if plan.queries else [plan.focus]
    tasks = [
        search_tool.execute(query=q, focus=plan.focus, max_results=4)
        for q in queries
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    valid_blocks: list[str] = []
    seen_snippets: set[str] = set()
    total_items = 0

    for res in raw_results:
        if isinstance(res, str) and res.strip():
            lines = res.strip().split("\n\n")
            for block in lines:
                key = block[:60]
                if key not in seen_snippets and not block.startswith("Aucun"):
                    seen_snippets.add(key)
                    valid_blocks.append(block)
                    if block.startswith(("1.", "2.", "3.", "4.", "5.")):
                        total_items += 1

    consolidated = "\n\n".join(valid_blocks) if valid_blocks else "Aucune source trouvée."
    return consolidated, total_items, time.perf_counter() - t0


async def synthesize_findings(
    provider: LLMProvider,
    query: str,
    sources_text: str,
    user_profile: str,
) -> str:
    """Formule une synthèse scientifique et technique avec liens cliquables vérifiés."""
    sys_instruction = SYNTHESIZER_SYSTEM_PROMPT.replace("{user_profile}", user_profile)
    prompt = (
        f"Demande initiale : {query}\n\n"
        f"Sources documentaires collectées :\n{sources_text}\n\n"
        "Consigne : Formule la synthèse technique structurée avec les liens cliquables."
    )
    res = await provider.generate_text(prompt=prompt, system_instruction=sys_instruction)
    return res.strip() if res.strip() else sources_text


async def synthesize_findings_stream(
    provider: LLMProvider,
    query: str,
    sources_text: str,
    user_profile: str,
) -> AsyncIterator[str]:
    """Formule une synthèse scientifique et technique en flux continu (streaming)."""
    sys_instruction = SYNTHESIZER_SYSTEM_PROMPT.replace("{user_profile}", user_profile)
    prompt = (
        f"Demande initiale : {query}\n\n"
        f"Sources documentaires collectées :\n{sources_text}\n\n"
        "Consigne : Formule la synthèse technique structurée avec les liens cliquables."
    )
    async for chunk in provider.stream_text(prompt=prompt, system_instruction=sys_instruction):
        yield chunk
