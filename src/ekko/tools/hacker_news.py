"""HackerNewsTool capturing high-consensus technology and science signals from Hacker News."""

import json
import time
from typing import Any
import httpx
from pydantic import BaseModel, Field

from ekko.core.models import ToolResult
from ekko.tools.base import BaseTool
from ekko.utils.logger import get_logger

logger = get_logger("tools.hacker_news")

HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


def _build_query_params(days: int, min_score: int, limit: int) -> dict[str, Any]:
    """Construct Algolia query parameters applying freshness and consensus score filters."""
    cutoff_ts = int(time.time() - (days * 86400))
    return {
        "tags": "story",
        "numericFilters": f"points>={min_score},created_at_i>={cutoff_ts}",
        "hitsPerPage": limit,
    }


def _format_hit(hit: dict[str, Any]) -> dict[str, Any]:
    """Project raw Algolia hit into compact schema with URL fallback."""
    object_id = hit.get("objectID", "")
    url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
    return {
        "title": hit.get("title", "Untitled"),
        "url": url,
        "points": hit.get("points", 0),
        "comments": hit.get("num_comments", 0),
        "date": hit.get("created_at", ""),
    }


def _format_hits_response(hits: list[dict[str, Any]]) -> str:
    """Format hit list into JSON or friendly fallback message."""
    if not hits:
        return "No signals found matching the criteria."
    compact_items = [_format_hit(hit) for hit in hits]
    return json.dumps(compact_items, ensure_ascii=False)


class HackerNewsInput(BaseModel):
    """Input parameters for capturing high-consensus tech signals."""

    days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Time window in days for consensus watch (1 to 30 days).",
    )
    min_score: int = Field(
        default=150,
        ge=50,
        description="Minimum points threshold to filter noise and retain only consensus signals (minimum 50).",
    )
    limit: int = Field(
        default=20,
        ge=5,
        le=30,
        description="Number of top consensus items to retrieve (5 to 30).",
    )


class HackerNewsTool(BaseTool):
    """Tool capturing high-impact consensus signals and tech breakthroughs via Hacker News."""

    name: str = "hacker_news"
    description: str = (
        "Consensus radar capturing the highest-impact technology and science discussions, breakthroughs, "
        "and ecosystem shifts from Hacker News for a given period."
    )
    args_schema: type[BaseModel] = HackerNewsInput

    async def _run(
        self,
        days: int = 7,
        min_score: int = 150,
        limit: int = 20,
    ) -> ToolResult:
        """Execute consensus signal gathering query against Hacker News Algolia API."""
        params = _build_query_params(days, min_score, limit)
        logger.debug("Querying Algolia HN consensus radar with params: %s", params)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(HN_ALGOLIA_URL, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
        except httpx.RequestError as err:
            logger.warning("Network failure in HackerNewsTool: %s", err)
            return ToolResult(
                content=f"Network error while fetching signals: {err}",
                success=False,
                error=type(err).__name__,
            )

        hits = data.get("hits", [])
        return ToolResult(content=_format_hits_response(hits), success=True)
