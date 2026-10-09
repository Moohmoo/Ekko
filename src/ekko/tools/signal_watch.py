"""SignalWatchTool capturing high-impact technology and science signals from Hacker News."""

import json
import time
from typing import Any
import httpx
from pydantic import BaseModel, Field

from ekko.core.models import ToolResult
from ekko.tools.base import BaseTool
from ekko.utils.logger import get_logger

logger = get_logger("tools.signal_watch")

HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


def _build_query_params(
    query: str | None,
    days: int,
    min_score: int,
    limit: int,
) -> dict[str, Any]:
    """Construct Algolia query parameters applying freshness and score filters."""
    cutoff_ts = int(time.time() - (days * 86400))
    params: dict[str, Any] = {
        "tags": "story",
        "numericFilters": f"points>={min_score},created_at_i>={cutoff_ts}",
        "hitsPerPage": limit,
    }
    if query:
        params["query"] = query
    return params


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


class SignalWatchInput(BaseModel):
    """Input parameters for capturing tech and scientific signals."""

    query: str | None = Field(
        default=None,
        description=(
            "Optional targeted search term in concise English (e.g. 'vLLM', 'PostgreSQL', 'WebGPU'). "
            "Leave as None for broad or exploratory watch to scan top consensus signals without keyword bias."
        ),
    )
    days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Time window in days to enforce signal freshness (1 to 30 days).",
    )
    min_score: int = Field(
        default=150,
        ge=0,
        description="Minimum points/upvotes threshold to filter out noise.",
    )
    limit: int = Field(
        default=15,
        ge=1,
        le=30,
        description="Maximum number of items to retrieve (1 to 30).",
    )


class SignalWatchTool(BaseTool):
    """Tool capturing high-impact signals and ecosystem breakthroughs via Hacker News Algolia API."""

    name: str = "signal_watch"
    description: str = (
        "Captures emerging technology and science signals, breakthroughs, and ecosystem shifts "
        "from Hacker News without requiring external API keys."
    )
    args_schema: type[BaseModel] = SignalWatchInput

    async def _run(
        self,
        query: str | None = None,
        days: int = 7,
        min_score: int = 150,
        limit: int = 15,
    ) -> ToolResult:
        """Execute signal gathering query against Hacker News Algolia API."""
        params = _build_query_params(query, days, min_score, limit)
        logger.debug("Querying Algolia HN with params: %s", params)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(HN_ALGOLIA_URL, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
        except httpx.RequestError as err:
            logger.warning("Network failure in SignalWatchTool: %s", err)
            return ToolResult(
                content=f"Network error while fetching signals: {err}",
                success=False,
                error=type(err).__name__,
            )

        hits = data.get("hits", [])
        return ToolResult(content=_format_hits_response(hits), success=True)
