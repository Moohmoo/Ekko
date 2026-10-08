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
from .context import ExecutionContext
from .schemas import SearchPlan


from .prompts import build_research_planner_prompt, build_synthesis_prompt


async def plan_research(
    provider: LLMProvider,
    query: str,
    history_context: str = "",
    ctx: ExecutionContext | None = None,
) -> SearchPlan:
    """Cadre l'intention et génère les requêtes de recherche ciblées en anglais."""
    prompt = f"Demande utilisateur : {query}"
    if history_context:
        prompt = f"{history_context}\n\n{prompt}"
    sys_instruction = build_research_planner_prompt(ctx)
    plan = await provider.generate_structured(
        prompt=prompt,
        schema=SearchPlan,
        system_instruction=sys_instruction,
    )
    if not plan.queries:
        plan.queries = [query.strip()]
    return plan


async def collect_sources(
    search_tool: SearchTool,
    plan: SearchPlan,
) -> tuple[str, int, float]:
    """Interroge les moteurs de recherche en parallèle et dédoublonne les observations."""
    t0 = time.perf_counter()
    queries = [q.strip() for q in plan.queries[:2] if q.strip()]
    if not queries:
        return "Aucune source trouvée.", 0, 0.0

    limit = 6 if plan.focus == "news" else 4
    tasks = [
        search_tool.execute(query=q, focus=plan.focus, max_results=limit)
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
                    if block.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.")):
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
    sys_instruction = build_synthesis_prompt(user_profile)
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
    sys_instruction = build_synthesis_prompt(user_profile)
    prompt = (
        f"Demande initiale : {query}\n\n"
        f"Sources documentaires collectées :\n{sources_text}\n\n"
        "Consigne : Formule la synthèse technique structurée avec les liens cliquables."
    )
    async for chunk in provider.stream_text(prompt=prompt, system_instruction=sys_instruction):
        yield chunk
