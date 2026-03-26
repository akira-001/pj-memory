"""Memory consolidation dashboard route."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..services.consolidation_service import get_crystallization_data

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def consolidation_page(request: Request):
    config = request.app.state.config
    templates = request.app.state.templates
    data = get_crystallization_data(config)

    return templates.TemplateResponse(
        "consolidation/index.html",
        {
            "request": request,
            "active_page": "consolidation",
            "data": data,
        },
    )
