"""Memory search routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ...store import MemoryStore
from ..services.memory_service import get_memory_summary, get_top_keywords

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def search_page(request: Request):
    """Render search page with optional initial results."""
    config = request.app.state.config
    templates = request.app.state.templates
    q = request.query_params.get("q", "")
    results = []
    status = ""

    if q:
        with MemoryStore(config) as store:
            response = store._execute_search(q, top_k=10)
            results = response.results
            status = response.status

    summary = get_memory_summary(config)
    top_keywords = get_top_keywords(config, limit=10)

    return templates.TemplateResponse(
        request,
        "search/index.html",
        {
            "active_page": "search",
            "query": q,
            "results": results,
            "status": status,
            "summary": summary,
            "top_keywords": top_keywords,
        },
    )


@router.get("/api/results", response_class=HTMLResponse)
async def search_results(request: Request):
    """HTMX partial: search results only."""
    config = request.app.state.config
    templates = request.app.state.templates
    q = request.query_params.get("q", "")

    if not q:
        return HTMLResponse('<div class="empty-state">Enter a search query</div>')

    with MemoryStore(config) as store:
        response = store._execute_search(q, top_k=10)

    return templates.TemplateResponse(
        request,
        "search/_results.html",
        {
            "results": response.results,
            "status": response.status,
            "query": q,
        },
    )
