"""Ollama service — process, model, and LaunchAgent management."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from ...config import CogMemConfig

_DEFAULT_BASE_URL = "http://localhost:11434"
_TIMEOUT = 2


def _api_get(path: str, *, base_url: str = _DEFAULT_BASE_URL, timeout: int = _TIMEOUT) -> dict[str, Any] | None:
    """GET an Ollama API endpoint. Returns parsed JSON or None on failure."""
    try:
        req = urllib.request.Request(f"{base_url}{path}")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def get_status(*, base_url: str = _DEFAULT_BASE_URL) -> str:
    """Check if Ollama is running. Returns 'running' or 'stopped'."""
    result = _api_get("/api/tags", base_url=base_url)
    return "running" if result is not None else "stopped"


def get_models(*, base_url: str = _DEFAULT_BASE_URL) -> list[dict[str, Any]]:
    """Get list of available models. Returns empty list if Ollama is stopped."""
    result = _api_get("/api/tags", base_url=base_url)
    if result is None:
        return []
    return result.get("models", [])


def check_embedding_model(
    config: CogMemConfig, *, base_url: str = _DEFAULT_BASE_URL
) -> dict[str, Any]:
    """Check if the configured embedding model is available.

    Returns dict with keys: status ('loaded'|'not_found'|'unavailable'), name, size.
    """
    model_name = config.embedding_model
    models = get_models(base_url=base_url)
    if not models and get_status(base_url=base_url) == "stopped":
        return {"status": "unavailable", "name": model_name, "size": None}
    for m in models:
        if m["name"].split(":")[0] == model_name or m["name"] == model_name:
            return {"status": "loaded", "name": model_name, "size": m.get("size")}
    return {"status": "not_found", "name": model_name, "size": None}
