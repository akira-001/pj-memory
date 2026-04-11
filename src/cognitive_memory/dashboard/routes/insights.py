"""Insights dashboard route."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..services.insights_service import get_insights_data

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def insights_page(request: Request):
    config = request.app.state.config
    templates = request.app.state.templates
    days_param = request.query_params.get("days")
    days = int(days_param) if days_param and days_param.isdigit() else None
    data = get_insights_data(config, days=days)
    return templates.TemplateResponse(
        request,
        "insights/index.html",
        {
            "active_page": "insights",
            "data": data,
            "selected_days": days,
        },
    )
