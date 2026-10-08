"""Pipeline de recherche documentaire et revue scientifique pour Ekko.

Implémente le workflow déterministe en 3 étapes spécialisées :
Cadrage & Expansion de requêtes -> Collecte & Dédoublonnage -> Synthèse certifiée.
"""

import asyncio
from collections.abc import AsyncIterator
import time
from typing import Any
from providers.base import LLMProvider
from tools.search.tool import SearchItem, SearchTool
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


def _deduplicate_items(raw_results: list[object]) -> list[SearchItem]:
    """Extrait et dédoublonne les items de recherche par URL unique."""
    unique: list[SearchItem] = []
    seen: set[str] = set()
    for res in raw_results:
        if not isinstance(res, list):
            continue
        for item in res:
            if isinstance(item, SearchItem) and item.url and item.url not in seen:
                seen.add(item.url)
                unique.append(item)
    return unique


async def collect_sources(
    search_tool: SearchTool,
    plan: SearchPlan,
) -> tuple[str, int, float]:
    """Interroge les moteurs de recherche en parallèle et dédoublonne les observations."""
    t0 = time.perf_counter()
    seen_q: set[str] = set()
    queries: list[str] = []
    for q in plan.queries:
        clean_q = q.strip()
        if clean_q and clean_q.lower() not in seen_q:
            seen_q.add(clean_q.lower())
            queries.append(clean_q)
        if len(queries) >= 2:
            break

    if not queries:
        return "Aucune source trouvée.", 0, 0.0

    limit = 6 if plan.focus == "news" else 4
    tasks = [
        search_tool.search(query=q, focus=plan.focus, max_results=limit)
        for q in queries
    ]
    raw = await asyncio.gather(*tasks, return_exceptions=True)
    items = _deduplicate_items(list(raw))

    if not items:
        return "Aucune source trouvée.", 0, time.perf_counter() - t0

    consolidated = search_tool.format_results(items, query=" ".join(queries), focus=plan.focus)
    return consolidated, len(items), time.perf_counter() - t0


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
