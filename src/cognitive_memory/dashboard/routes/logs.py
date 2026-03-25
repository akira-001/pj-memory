"""Log browser routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..services.logs_service import get_log_dates, get_log_entries

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def logs_list(request: Request):
    """Render the log dates list page."""
    config = request.app.state.config
    templates = request.app.state.templates
    dates = get_log_dates(config)
    return templates.TemplateResponse(
        "logs/list.html",
        {
            "request": request,
            "active_page": "logs",
            "dates": dates,
        },
    )


@router.get("/api/entries", response_class=HTMLResponse)
async def filtered_entries(request: Request):
    """HTMX partial: return filtered entries HTML fragment."""
    config = request.app.state.config
    templates = request.app.state.templates
    date = request.query_params.get("date", "")
    category = request.query_params.get("category") or None
    sort = request.query_params.get("sort", "time")
    q = request.query_params.get("q") or None

    data = get_log_entries(config, date, category=category, sort=sort, query=q)
    entries = data["entries"] if data else []

    return templates.TemplateResponse(
        "logs/_entries.html",
        {
            "request": request,
            "entries": entries,
        },
    )


@router.get("/{date}", response_class=HTMLResponse)
async def log_detail(request: Request, date: str):
    """Render the log detail page for a specific date."""
    config = request.app.state.config
    templates = request.app.state.templates
    category = request.query_params.get("category") or None
    sort = request.query_params.get("sort", "time")
    q = request.query_params.get("q") or None

    data = get_log_entries(config, date, category=category, sort=sort, query=q)

    if data is None:
        return templates.TemplateResponse(
            "logs/detail.html",
            {
                "request": request,
                "active_page": "logs",
                "data": None,
                "date": date,
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        "logs/detail.html",
        {
            "request": request,
            "active_page": "logs",
            "data": data,
            "date": date,
        },
    )
