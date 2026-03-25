"""Memory overview routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ...signals import check_signals
from ..services.memory_service import get_overview_data

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def overview(request: Request):
    """Render the Memory Overview page."""
    config = request.app.state.config
    templates = request.app.state.templates
    data = get_overview_data(config)
    signals = check_signals(config)
    return templates.TemplateResponse(
        "memory/overview.html",
        {
            "request": request,
            "active_page": "memory",
            "data": data,
            "signals": signals,
        },
    )
