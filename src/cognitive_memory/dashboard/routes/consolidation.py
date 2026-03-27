"""Memory consolidation dashboard route."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..services.consolidation_service import (
    get_crystallization_data,
    get_decay_settings,
    save_decay_settings,
)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def consolidation_page(request: Request):
    config = request.app.state.config
    templates = request.app.state.templates
    data = get_crystallization_data(config)
    decay = get_decay_settings(config)

    return templates.TemplateResponse(
        "consolidation/index.html",
        {
            "request": request,
            "active_page": "consolidation",
            "data": data,
            "decay": decay,
        },
    )


@router.post("/decay")
async def update_decay_settings(request: Request):
    form = await request.form()
    config = request.app.state.config
    settings = {
        "arousal_threshold": float(form.get("arousal_threshold", 0.7)),
        "recall_threshold": int(form.get("recall_threshold", 2)),
        "recall_window_months": int(form.get("recall_window_months", 18)),
        "enabled": "enabled" in form,
    }
    save_decay_settings(config, settings)
    # Update in-memory config
    config.decay_arousal_threshold = settings["arousal_threshold"]
    config.decay_recall_threshold = settings["recall_threshold"]
    config.decay_recall_window_months = settings["recall_window_months"]
    config.decay_enabled = settings["enabled"]
    return RedirectResponse(url="/consolidation", status_code=303)
