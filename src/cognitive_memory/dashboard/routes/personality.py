"""Personality routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..services.personality_service import get_personality_data

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def personality_page(request: Request):
    """Personality overview page."""
    config = request.app.state.config
    templates = request.app.state.templates
    data = get_personality_data(config)
    return templates.TemplateResponse(
        "personality/index.html",
        {
            "request": request,
            "active_page": "personality",
            "data": data,
        },
    )
