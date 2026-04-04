"""Ollama service — process, model, and LaunchAgent management."""

from __future__ import annotations

import json
import plistlib
import shutil
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

from ...config import CogMemConfig

_DEFAULT_BASE_URL = "http://localhost:11434"
_TIMEOUT = 2
_LAUNCHAGENT_PATH = Path.home() / "Library" / "LaunchAgents" / "com.ollama.serve.plist"


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


# ---------------------------------------------------------------------------
# Task 2: Process Control
# ---------------------------------------------------------------------------


def is_ollama_installed() -> bool:
    """Return True if the ollama binary is on PATH."""
    return shutil.which("ollama") is not None


def start_serve(*, base_url: str = _DEFAULT_BASE_URL) -> dict[str, Any]:
    """Start `ollama serve` as a detached background process.

    Waits up to 2 seconds then verifies the server is reachable.
    Returns {"ok": True} on success or {"ok": False, "error": str} on failure.
    """
    if not is_ollama_installed():
        return {"ok": False, "error": "ollama not installed (not found on PATH)"}
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    time.sleep(2)
    status = get_status(base_url=base_url)
    if status == "running":
        return {"ok": True}
    return {"ok": False, "error": "ollama serve started but server is not responding"}


def stop_serve() -> dict[str, Any]:
    """Stop the running `ollama serve` process via pgrep / kill.

    Returns {"ok": True} on success or {"ok": False, "error": str} on failure.
    """
    result = subprocess.run(
        ["pgrep", "-f", "ollama serve"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return {"ok": False, "error": "ollama serve is not running"}
    pids = result.stdout.strip().splitlines()
    for pid in pids:
        subprocess.run(["kill", pid.strip()], capture_output=True)
    return {"ok": True}


def restart_serve(*, base_url: str = _DEFAULT_BASE_URL) -> dict[str, Any]:
    """Stop then start `ollama serve`.

    Returns {"ok": True} on success or {"ok": False, "error": str} on failure.
    """
    stop_result = stop_serve()
    # If it was not running that is acceptable — proceed to start
    if not stop_result["ok"] and "not running" not in stop_result.get("error", "").lower():
        return stop_result
    return start_serve(base_url=base_url)
