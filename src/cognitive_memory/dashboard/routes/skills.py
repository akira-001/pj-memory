"""Skills management routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..services.skills_service import (
    get_audit_results,
    get_plugin_skills,
    get_skill_detail,
    get_skill_trend,
    get_skills_list,
    get_update_status,
)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def skills_list(request: Request):
    """Skills list page."""
    config = request.app.state.config
    templates = request.app.state.templates

    skills = get_skills_list(config)
    audit = get_audit_results(config)
    plugin_skills = get_plugin_skills(config)
    update_status = get_update_status(config)

    return templates.TemplateResponse(
        request,
        "skills/list.html",
        {
            "active_page": "skills",
            "skills": skills,
            "audit": audit,
            "auto_improve": config.skills_auto_improve,
            "plugin_skills": plugin_skills,
            "update_status": update_status,
        },
    )


@router.get("/api/audit", response_class=HTMLResponse)
async def audit_results(request: Request):
    """HTMX partial: audit results fragment."""
    config = request.app.state.config
    templates = request.app.state.templates

    audit = get_audit_results(config)

    return templates.TemplateResponse(
        request,
        "skills/_audit_fragment.html",
        {
            "audit": audit,
        },
    )


@router.get("/api/detail/{skill_id}", response_class=HTMLResponse)
async def skill_modal(request: Request, skill_id: str):
    """HTMX partial: skill detail modal."""
    config = request.app.state.config
    templates = request.app.state.templates

    detail = get_skill_detail(config, skill_id)
    if detail is None:
        return HTMLResponse(
            '<div class="empty-state">Skill not found</div>',
            status_code=404,
        )

    trend_data = get_skill_trend(config, skill_id)

    return templates.TemplateResponse(
        request,
        "skills/_detail_modal.html",
        {
            "skill": detail["skill"],
            "usage_log": detail["usage_log"],
            "events": detail["events"],
            "trend_data": trend_data,
        },
    )


@router.get("/{skill_id}", response_class=HTMLResponse)
async def skill_detail_page(request: Request, skill_id: str):
    """Skill detail page."""
    config = request.app.state.config
    templates = request.app.state.templates

    detail = get_skill_detail(config, skill_id)
    if detail is None:
        return HTMLResponse(
            content="<h1>Skill not found</h1>",
            status_code=404,
        )

    trend_data = get_skill_trend(config, skill_id)

    return templates.TemplateResponse(
        request,
        "skills/detail.html",
        {
            "active_page": "skills",
            "skill": detail["skill"],
            "usage_log": detail["usage_log"],
            "events": detail["events"],
            "trend_data": trend_data,
        },
    )
