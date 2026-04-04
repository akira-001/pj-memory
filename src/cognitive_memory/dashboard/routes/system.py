"""System management routes — Ollama process, model, and LaunchAgent."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..services import ollama_service

router = APIRouter()


def _base_url(request: Request) -> str:
    """Get Ollama base URL from config or default."""
    config = request.app.state.config
    url = getattr(config, "embedding_url", "http://localhost:11434/api/embed")
    if url.endswith("/api/embed"):
        return url[: -len("/api/embed")]
    return "http://localhost:11434"


def _system_context(request: Request) -> dict:
    """Build common template context for system page."""
    base_url = _base_url(request)
    config = request.app.state.config
    return {
        "active_page": "system",
        "installed": ollama_service.is_ollama_installed(),
        "ollama_status": ollama_service.get_status(base_url=base_url),
        "model_info": ollama_service.check_embedding_model(config, base_url=base_url),
        "launchagent": ollama_service.get_launchagent_status(),
    }


@router.get("/", response_class=HTMLResponse)
async def system_page(request: Request):
    templates = request.app.state.templates
    ctx = _system_context(request)
    return templates.TemplateResponse(request, "system/index.html", ctx)


@router.post("/ollama/start", response_class=HTMLResponse)
async def ollama_start(request: Request):
    base_url = _base_url(request)
    ollama_service.start_serve(base_url=base_url)
    templates = request.app.state.templates
    ctx = _system_context(request)
    return templates.TemplateResponse(request, "system/_process.html", ctx)


@router.post("/ollama/stop", response_class=HTMLResponse)
async def ollama_stop(request: Request):
    ollama_service.stop_serve()
    templates = request.app.state.templates
    ctx = _system_context(request)
    return templates.TemplateResponse(request, "system/_process.html", ctx)


@router.post("/ollama/restart", response_class=HTMLResponse)
async def ollama_restart(request: Request):
    base_url = _base_url(request)
    ollama_service.restart_serve(base_url=base_url)
    templates = request.app.state.templates
    ctx = _system_context(request)
    return templates.TemplateResponse(request, "system/_process.html", ctx)


@router.post("/model/pull", response_class=HTMLResponse)
async def model_pull(request: Request):
    config = request.app.state.config
    base_url = _base_url(request)
    ollama_service.pull_model(config.embedding_model, base_url=base_url)
    templates = request.app.state.templates
    ctx = _system_context(request)
    return templates.TemplateResponse(request, "system/_model.html", ctx)


@router.delete("/model/delete", response_class=HTMLResponse)
async def model_delete(request: Request):
    config = request.app.state.config
    base_url = _base_url(request)
    ollama_service.delete_model(config.embedding_model, base_url=base_url)
    templates = request.app.state.templates
    ctx = _system_context(request)
    return templates.TemplateResponse(request, "system/_model.html", ctx)


@router.post("/launchagent/toggle", response_class=HTMLResponse)
async def launchagent_toggle(request: Request):
    current = ollama_service.get_launchagent_status()
    ollama_service.set_launchagent(not current["enabled"])
    templates = request.app.state.templates
    ctx = _system_context(request)
    return templates.TemplateResponse(request, "system/_launchagent.html", ctx)
