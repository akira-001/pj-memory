"""Memory overview routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ...signals import check_signals
from ..services import ollama_service
from ..services.memory_service import get_overview_data

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def overview(request: Request):
    """Render the Memory Overview page."""
    config = request.app.state.config
    templates = request.app.state.templates
    data = get_overview_data(config)
    signals = check_signals(config)
    ollama_status = ollama_service.get_status()
    ollama_model = ollama_service.check_embedding_model(config)
    return templates.TemplateResponse(
        request,
        "memory/overview.html",
        {
            "active_page": "memory",
            "data": data,
            "signals": signals,
            "ollama_status": ollama_status,
            "ollama_model": ollama_model,
        },
    )
