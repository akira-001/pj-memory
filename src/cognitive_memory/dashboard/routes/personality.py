"""Personality routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from ..services.personality_service import get_personality_data, update_section

router = APIRouter()


class SectionUpdate(BaseModel):
    target: str  # "user" or "soul"
    section: str
    content: str


@router.get("/", response_class=HTMLResponse)
async def personality_page(request: Request):
    """Personality overview page."""
    config = request.app.state.config
    templates = request.app.state.templates
    data = get_personality_data(config)
    return templates.TemplateResponse(
        request,
        "personality/index.html",
        {
            "active_page": "personality",
            "data": data,
        },
    )


@router.post("/api/section", response_class=JSONResponse)
async def update_personality_section(request: Request, body: SectionUpdate):
    """Update a single section of user or soul identity."""
    config = request.app.state.config
    try:
        update_section(config, body.target, body.section, body.content)
        return {"status": "ok"}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
