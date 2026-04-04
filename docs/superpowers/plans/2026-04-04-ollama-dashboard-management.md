# Ollama Dashboard Management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Ollama process/model/auto-start management to the cogmem dashboard — a status card on the overview page and a dedicated `/system` page.

**Architecture:** New `ollama_service.py` handles all Ollama interactions via `urllib.request` and `subprocess` (no new dependencies). New `/system` route and template provide full management UI. Existing overview page gets a 5th stat-card showing Ollama status. All mutations use htmx partial updates.

**Tech Stack:** FastAPI, Jinja2, htmx, urllib.request, subprocess, plistlib (stdlib)

**Spec:** `docs/superpowers/specs/2026-04-04-ollama-dashboard-management-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/cognitive_memory/dashboard/services/ollama_service.py` | Create | All Ollama API, process, and LaunchAgent operations |
| `src/cognitive_memory/dashboard/routes/system.py` | Create | `/system` routes and htmx endpoints |
| `src/cognitive_memory/dashboard/templates/system/index.html` | Create | System management page template |
| `src/cognitive_memory/dashboard/templates/system/_process.html` | Create | Ollama process section (htmx fragment) |
| `src/cognitive_memory/dashboard/templates/system/_model.html` | Create | Embedding model section (htmx fragment) |
| `src/cognitive_memory/dashboard/templates/system/_launchagent.html` | Create | Auto-start toggle section (htmx fragment) |
| `src/cognitive_memory/dashboard/templates/memory/_ollama_card.html` | Create | Ollama stat-card fragment for overview |
| `tests/test_dashboard/test_ollama_service.py` | Create | Unit tests for ollama_service |
| `tests/test_dashboard/test_system_routes.py` | Create | Route tests for /system |
| `src/cognitive_memory/dashboard/app.py` | Modify | Register system router |
| `src/cognitive_memory/dashboard/templates/base.html` | Modify | Add System nav link |
| `src/cognitive_memory/dashboard/templates/memory/overview.html` | Modify | Add Ollama stat-card |
| `src/cognitive_memory/dashboard/routes/memory.py` | Modify | Pass Ollama status to template |
| `src/cognitive_memory/dashboard/i18n.py` | Modify | Add system translation keys |
| `src/cognitive_memory/dashboard/static/style.css` | Modify | Add toggle switch and system page styles |

---

### Task 1: ollama_service.py — Status and Model Queries

**Files:**
- Create: `src/cognitive_memory/dashboard/services/ollama_service.py`
- Create: `tests/test_dashboard/test_ollama_service.py`

- [ ] **Step 1: Write failing tests for `get_status()` and `get_models()`**

```python
"""Tests for ollama_service — status and model queries."""

from __future__ import annotations

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from unittest.mock import patch

import pytest

from cognitive_memory.dashboard.services.ollama_service import (
    get_status,
    get_models,
    check_embedding_model,
)
from cognitive_memory.config import CogMemConfig


class FakeOllamaHandler(BaseHTTPRequestHandler):
    """Minimal Ollama API stub."""

    models = [
        {"name": "zylonai/multilingual-e5-large:latest", "size": 1300000000,
         "modified_at": "2026-03-01T00:00:00Z"},
    ]

    def do_GET(self):
        if self.path == "/api/tags":
            body = json.dumps({"models": self.models}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def log_message(self, *args):
        pass  # suppress logs


@pytest.fixture
def fake_ollama():
    """Start a fake Ollama server and return its base URL."""
    server = HTTPServer(("127.0.0.1", 0), FakeOllamaHandler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


class TestGetStatus:
    def test_running(self, fake_ollama):
        status = get_status(base_url=fake_ollama)
        assert status == "running"

    def test_stopped_when_unreachable(self):
        status = get_status(base_url="http://127.0.0.1:19999")
        assert status == "stopped"


class TestGetModels:
    def test_returns_model_list(self, fake_ollama):
        models = get_models(base_url=fake_ollama)
        assert len(models) == 1
        assert models[0]["name"] == "zylonai/multilingual-e5-large:latest"
        assert models[0]["size"] == 1300000000

    def test_empty_when_stopped(self):
        models = get_models(base_url="http://127.0.0.1:19999")
        assert models == []


class TestCheckEmbeddingModel:
    def test_model_found(self, fake_ollama, tmp_path):
        (tmp_path / "cogmem.toml").write_text(
            '[cogmem]\nembedding_model = "zylonai/multilingual-e5-large"\n'
            f'embedding_url = "{fake_ollama}/api/embed"\n',
            encoding="utf-8",
        )
        config = CogMemConfig.from_toml(tmp_path / "cogmem.toml")
        result = check_embedding_model(config, base_url=fake_ollama)
        assert result["status"] == "loaded"
        assert result["name"] == "zylonai/multilingual-e5-large"

    def test_model_not_found(self, fake_ollama, tmp_path):
        (tmp_path / "cogmem.toml").write_text(
            '[cogmem]\nembedding_model = "nonexistent-model"\n'
            f'embedding_url = "{fake_ollama}/api/embed"\n',
            encoding="utf-8",
        )
        config = CogMemConfig.from_toml(tmp_path / "cogmem.toml")
        result = check_embedding_model(config, base_url=fake_ollama)
        assert result["status"] == "not_found"

    def test_ollama_stopped(self, tmp_path):
        (tmp_path / "cogmem.toml").write_text(
            '[cogmem]\nembedding_model = "zylonai/multilingual-e5-large"\n',
            encoding="utf-8",
        )
        config = CogMemConfig.from_toml(tmp_path / "cogmem.toml")
        result = check_embedding_model(config, base_url="http://127.0.0.1:19999")
        assert result["status"] == "unavailable"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_dashboard/test_ollama_service.py -v`
Expected: ModuleNotFoundError — `ollama_service` doesn't exist yet

- [ ] **Step 3: Implement `ollama_service.py` — status and model functions**

```python
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
        # Ollama model names may include :tag suffix
        if m["name"].split(":")[0] == model_name or m["name"] == model_name:
            return {"status": "loaded", "name": model_name, "size": m.get("size")}
    return {"status": "not_found", "name": model_name, "size": None}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_dashboard/test_ollama_service.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/cognitive_memory/dashboard/services/ollama_service.py tests/test_dashboard/test_ollama_service.py
git commit -m "feat(dashboard): add ollama_service — status and model queries"
```

---

### Task 2: ollama_service.py — Process Control

**Files:**
- Modify: `src/cognitive_memory/dashboard/services/ollama_service.py`
- Modify: `tests/test_dashboard/test_ollama_service.py`

- [ ] **Step 1: Write failing tests for process control**

Append to `tests/test_dashboard/test_ollama_service.py`:

```python
import shutil
import signal
import subprocess
from unittest.mock import patch, MagicMock

from cognitive_memory.dashboard.services.ollama_service import (
    is_ollama_installed,
    start_serve,
    stop_serve,
)


class TestIsOllamaInstalled:
    def test_installed(self):
        with patch("shutil.which", return_value="/usr/local/bin/ollama"):
            assert is_ollama_installed() is True

    def test_not_installed(self):
        with patch("shutil.which", return_value=None):
            assert is_ollama_installed() is False


class TestStartServe:
    @patch("cognitive_memory.dashboard.services.ollama_service.get_status")
    @patch("subprocess.Popen")
    @patch("shutil.which", return_value="/usr/local/bin/ollama")
    def test_start_success(self, mock_which, mock_popen, mock_status):
        mock_status.return_value = "running"
        result = start_serve()
        assert result["ok"] is True
        mock_popen.assert_called_once()

    @patch("shutil.which", return_value=None)
    def test_start_not_installed(self, mock_which):
        result = start_serve()
        assert result["ok"] is False
        assert "not found" in result["error"].lower() or "not installed" in result["error"].lower()


class TestStopServe:
    @patch("subprocess.run")
    def test_stop_success(self, mock_run):
        # pgrep returns PID
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="12345\n"),  # pgrep
            MagicMock(returncode=0),  # kill
        ]
        result = stop_serve()
        assert result["ok"] is True

    @patch("subprocess.run")
    def test_stop_not_running(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = stop_serve()
        assert result["ok"] is False
        assert "not running" in result["error"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_dashboard/test_ollama_service.py::TestIsOllamaInstalled -v`
Expected: ImportError — functions not defined yet

- [ ] **Step 3: Implement process control functions**

Append to `ollama_service.py`:

```python
import shutil
import subprocess
import time


def is_ollama_installed() -> bool:
    """Check if ollama binary is on PATH."""
    return shutil.which("ollama") is not None


def start_serve(*, base_url: str = _DEFAULT_BASE_URL) -> dict[str, Any]:
    """Start `ollama serve` as a detached process."""
    ollama_path = shutil.which("ollama")
    if not ollama_path:
        return {"ok": False, "error": "Ollama not installed"}
    try:
        subprocess.Popen(
            [ollama_path, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(2)
        status = get_status(base_url=base_url)
        return {"ok": status == "running"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def stop_serve() -> dict[str, Any]:
    """Stop the running `ollama serve` process."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "ollama serve"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return {"ok": False, "error": "Ollama not running"}
        pids = result.stdout.strip().split("\n")
        for pid in pids:
            subprocess.run(["kill", pid.strip()], timeout=5)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def restart_serve(*, base_url: str = _DEFAULT_BASE_URL) -> dict[str, Any]:
    """Restart `ollama serve`."""
    stop_result = stop_serve()
    time.sleep(1)
    return start_serve(base_url=base_url)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_dashboard/test_ollama_service.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/cognitive_memory/dashboard/services/ollama_service.py tests/test_dashboard/test_ollama_service.py
git commit -m "feat(dashboard): add ollama process control (start/stop/restart)"
```

---

### Task 3: ollama_service.py — Model Pull/Delete

**Files:**
- Modify: `src/cognitive_memory/dashboard/services/ollama_service.py`
- Modify: `tests/test_dashboard/test_ollama_service.py`

- [ ] **Step 1: Write failing tests for pull and delete**

Append to `tests/test_dashboard/test_ollama_service.py`:

```python
from cognitive_memory.dashboard.services.ollama_service import (
    pull_model,
    delete_model,
)


class FakeOllamaPullDeleteHandler(BaseHTTPRequestHandler):
    """Handles POST /api/pull and DELETE /api/delete."""

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length)) if content_length else {}
        if self.path == "/api/pull":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode())
        else:
            self.send_error(404)

    def do_DELETE(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length)) if content_length else {}
        if self.path == "/api/delete":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_error(404)

    def log_message(self, *args):
        pass


@pytest.fixture
def fake_ollama_pull_delete():
    server = HTTPServer(("127.0.0.1", 0), FakeOllamaPullDeleteHandler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


class TestPullModel:
    def test_pull_success(self, fake_ollama_pull_delete):
        result = pull_model("zylonai/multilingual-e5-large", base_url=fake_ollama_pull_delete)
        assert result["ok"] is True

    def test_pull_when_stopped(self):
        result = pull_model("some-model", base_url="http://127.0.0.1:19999")
        assert result["ok"] is False


class TestDeleteModel:
    def test_delete_success(self, fake_ollama_pull_delete):
        result = delete_model("zylonai/multilingual-e5-large", base_url=fake_ollama_pull_delete)
        assert result["ok"] is True

    def test_delete_when_stopped(self):
        result = delete_model("some-model", base_url="http://127.0.0.1:19999")
        assert result["ok"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_dashboard/test_ollama_service.py::TestPullModel -v`
Expected: ImportError

- [ ] **Step 3: Implement pull and delete**

Append to `ollama_service.py`:

```python
def pull_model(
    model_name: str, *, base_url: str = _DEFAULT_BASE_URL, timeout: int = 300
) -> dict[str, Any]:
    """Pull a model via Ollama API."""
    try:
        data = json.dumps({"name": model_name, "stream": False}).encode()
        req = urllib.request.Request(
            f"{base_url}/api/pull",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def delete_model(
    model_name: str, *, base_url: str = _DEFAULT_BASE_URL
) -> dict[str, Any]:
    """Delete a model via Ollama API."""
    try:
        data = json.dumps({"name": model_name}).encode()
        req = urllib.request.Request(
            f"{base_url}/api/delete",
            data=data,
            headers={"Content-Type": "application/json"},
            method="DELETE",
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_dashboard/test_ollama_service.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/cognitive_memory/dashboard/services/ollama_service.py tests/test_dashboard/test_ollama_service.py
git commit -m "feat(dashboard): add ollama model pull and delete"
```

---

### Task 4: ollama_service.py — LaunchAgent Management

**Files:**
- Modify: `src/cognitive_memory/dashboard/services/ollama_service.py`
- Modify: `tests/test_dashboard/test_ollama_service.py`

- [ ] **Step 1: Write failing tests for LaunchAgent**

Append to `tests/test_dashboard/test_ollama_service.py`:

```python
from pathlib import Path
from cognitive_memory.dashboard.services.ollama_service import (
    get_launchagent_status,
    set_launchagent,
    _LAUNCHAGENT_PATH,
)


class TestLaunchAgent:
    def test_status_no_plist(self, tmp_path):
        fake_path = tmp_path / "com.ollama.serve.plist"
        with patch.object(
            __import__("cognitive_memory.dashboard.services.ollama_service",
                       fromlist=["_LAUNCHAGENT_PATH"]),
            "_launchagent_path", return_value=fake_path,
        ):
            result = get_launchagent_status(plist_path=fake_path)
        assert result["enabled"] is False
        assert result["path"] == str(fake_path)

    def test_status_with_plist(self, tmp_path):
        fake_path = tmp_path / "com.ollama.serve.plist"
        fake_path.write_text('<?xml version="1.0"?><plist></plist>')
        result = get_launchagent_status(plist_path=fake_path)
        assert result["enabled"] is True

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/local/bin/ollama")
    def test_enable_creates_plist(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        fake_path = tmp_path / "com.ollama.serve.plist"
        result = set_launchagent(True, plist_path=fake_path)
        assert result["ok"] is True
        assert fake_path.exists()

    @patch("subprocess.run")
    def test_disable_removes_plist(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        fake_path = tmp_path / "com.ollama.serve.plist"
        fake_path.write_text('<?xml version="1.0"?><plist></plist>')
        result = set_launchagent(False, plist_path=fake_path)
        assert result["ok"] is True
        assert not fake_path.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_dashboard/test_ollama_service.py::TestLaunchAgent -v`
Expected: ImportError

- [ ] **Step 3: Implement LaunchAgent functions**

Append to `ollama_service.py`:

```python
import plistlib
from pathlib import Path

_LAUNCHAGENT_PATH = Path.home() / "Library" / "LaunchAgents" / "com.ollama.serve.plist"


def get_launchagent_status(
    *, plist_path: Path = _LAUNCHAGENT_PATH,
) -> dict[str, Any]:
    """Check if Ollama LaunchAgent is configured."""
    return {
        "enabled": plist_path.exists(),
        "path": str(plist_path),
    }


def set_launchagent(
    enabled: bool,
    *,
    plist_path: Path = _LAUNCHAGENT_PATH,
) -> dict[str, Any]:
    """Enable or disable Ollama LaunchAgent."""
    try:
        if enabled:
            ollama_path = shutil.which("ollama") or "/usr/local/bin/ollama"
            plist_data = {
                "Label": "com.ollama.serve",
                "ProgramArguments": [ollama_path, "serve"],
                "RunAtLoad": True,
                "KeepAlive": True,
            }
            plist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(plist_path, "wb") as f:
                plistlib.dump(plist_data, f)
            subprocess.run(
                ["launchctl", "load", str(plist_path)],
                capture_output=True, timeout=5,
            )
        else:
            if plist_path.exists():
                subprocess.run(
                    ["launchctl", "unload", str(plist_path)],
                    capture_output=True, timeout=5,
                )
                plist_path.unlink()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_dashboard/test_ollama_service.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/cognitive_memory/dashboard/services/ollama_service.py tests/test_dashboard/test_ollama_service.py
git commit -m "feat(dashboard): add LaunchAgent management for ollama"
```

---

### Task 5: i18n — System Translation Keys

**Files:**
- Modify: `src/cognitive_memory/dashboard/i18n.py`

- [ ] **Step 1: Add system translation keys**

Add the following entries to the `TRANSLATIONS` dict in `i18n.py`, before the `# Common` section:

```python
    # System
    "nav.system": {"en": "System", "ja": "システム"},
    "system.title": {"en": "System", "ja": "システム"},
    "system.subtitle": {"en": "Ollama process and embedding model management", "ja": "Ollama プロセスと埋め込みモデルの管理"},
    "system.ollama_process": {"en": "Ollama Process", "ja": "Ollama プロセス"},
    "system.process_desc": {"en": "ollama serve process control", "ja": "ollama serve プロセス制御"},
    "system.start": {"en": "Start", "ja": "起動"},
    "system.stop": {"en": "Stop", "ja": "停止"},
    "system.restart": {"en": "Restart", "ja": "再起動"},
    "system.running": {"en": "Running", "ja": "起動中"},
    "system.stopped": {"en": "Stopped", "ja": "停止中"},
    "system.not_installed": {"en": "Ollama not found", "ja": "Ollama が見つかりません"},
    "system.embedding_model": {"en": "Embedding Model", "ja": "埋め込みモデル"},
    "system.model_desc": {"en": "cogmem.toml: embedding_model", "ja": "cogmem.toml: embedding_model"},
    "system.model_name": {"en": "Model", "ja": "モデル"},
    "system.model_size": {"en": "Size", "ja": "サイズ"},
    "system.model_status": {"en": "Status", "ja": "状態"},
    "system.model_action": {"en": "Action", "ja": "操作"},
    "system.model_loaded": {"en": "Loaded", "ja": "ロード済み"},
    "system.model_not_found": {"en": "Not Found", "ja": "未取得"},
    "system.model_unavailable": {"en": "Unavailable", "ja": "利用不可"},
    "system.pull": {"en": "Pull Model", "ja": "モデル取得"},
    "system.pulling": {"en": "Pulling...", "ja": "取得中..."},
    "system.delete": {"en": "Delete", "ja": "削除"},
    "system.autostart": {"en": "Auto-start on Login", "ja": "ログイン時の自動起動"},
    "system.autostart_desc": {"en": "macOS LaunchAgent", "ja": "macOS LaunchAgent"},
    "system.enabled": {"en": "Enabled", "ja": "有効"},
    "system.disabled": {"en": "Disabled", "ja": "無効"},
    "system.embedding_unavailable": {"en": "Embedding unavailable", "ja": "埋め込み利用不可"},
    "system.model_missing": {"en": "Model not found", "ja": "モデル未取得"},
    "system.pull_required": {"en": "pull required", "ja": "取得が必要"},
```

- [ ] **Step 2: Verify no syntax errors**

Run: `python -c "from cognitive_memory.dashboard.i18n import t; print(t('nav.system', 'ja'))"`
Expected: `システム`

- [ ] **Step 3: Commit**

```bash
git add src/cognitive_memory/dashboard/i18n.py
git commit -m "feat(dashboard): add i18n keys for system page"
```

---

### Task 6: CSS — System Page Styles

**Files:**
- Modify: `src/cognitive_memory/dashboard/static/style.css`

- [ ] **Step 1: Add system page styles**

Append before the `/* Responsive */` section in `style.css`:

```css
/* System page */
.system-section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
    margin-bottom: 1.5rem;
}

.system-section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.system-section-title {
    font-size: 1rem;
    font-weight: 600;
}

.system-section-desc {
    font-size: 0.75rem;
    color: var(--text-dim);
    margin-top: 0.25rem;
}

.system-actions {
    display: flex;
    gap: 0.75rem;
}

.btn-sm {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 6px;
    font-size: 0.8125rem;
    cursor: pointer;
    transition: opacity 0.15s;
}

.btn-sm:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.btn-start { background: var(--success); color: white; }
.btn-stop { background: var(--error); color: white; }
.btn-restart { background: var(--text-dim); color: white; }
.btn-pull { background: var(--success); color: white; }
.btn-delete {
    background: none;
    color: var(--error);
    border: 1px solid var(--error);
}

.status-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    font-weight: 500;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
}

.status-dot--running { background: var(--success); }
.status-dot--stopped { background: var(--error); }
.status-dot--warning { background: var(--warning); }

/* Toggle switch */
.toggle-switch {
    position: relative;
    width: 44px;
    height: 24px;
    border-radius: 12px;
    cursor: pointer;
    transition: background 0.2s;
    border: none;
}

.toggle-switch--on { background: var(--success); }
.toggle-switch--off { background: var(--text-dim); }

.toggle-switch::after {
    content: '';
    position: absolute;
    top: 2px;
    width: 20px;
    height: 20px;
    background: white;
    border-radius: 50%;
    transition: left 0.2s;
}

.toggle-switch--on::after { left: 22px; }
.toggle-switch--off::after { left: 2px; }

/* Ollama stat card on overview */
.ollama-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
}

.nav-icon-gear { font-size: 1.1rem; }
```

- [ ] **Step 2: Verify CSS loads**

Run: `python -c "from pathlib import Path; css = Path('src/cognitive_memory/dashboard/static/style.css').read_text(); assert '.toggle-switch' in css; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/cognitive_memory/dashboard/static/style.css
git commit -m "feat(dashboard): add system page and toggle switch CSS"
```

---

### Task 7: Templates — System Page

**Files:**
- Create: `src/cognitive_memory/dashboard/templates/system/index.html`
- Create: `src/cognitive_memory/dashboard/templates/system/_process.html`
- Create: `src/cognitive_memory/dashboard/templates/system/_model.html`
- Create: `src/cognitive_memory/dashboard/templates/system/_launchagent.html`

- [ ] **Step 1: Create the system page template directory**

Run: `mkdir -p src/cognitive_memory/dashboard/templates/system`

- [ ] **Step 2: Create `index.html`**

```html
{% extends "base.html" %}
{% block title %}{{ t('system.title', get_lang(request)) }}{% endblock %}

{% block content %}
{% set lang = get_lang(request) %}
<div class="page-header">
    <h1>{{ t('system.title', lang) }}</h1>
    <p>{{ t('system.subtitle', lang) }}</p>
</div>

{% if not installed %}
<div class="alert alert-warning">
    {{ t('system.not_installed', lang) }}
</div>
{% endif %}

<div id="process-section">
    {% include "system/_process.html" %}
</div>

<div id="model-section">
    {% include "system/_model.html" %}
</div>

<div id="launchagent-section">
    {% include "system/_launchagent.html" %}
</div>
{% endblock %}
```

- [ ] **Step 3: Create `_process.html`**

```html
{% set lang = get_lang(request) %}
<div class="system-section">
    <div class="system-section-header">
        <div>
            <div class="system-section-title">{{ t('system.ollama_process', lang) }}</div>
            <div class="system-section-desc">{{ t('system.process_desc', lang) }}</div>
        </div>
        <div class="status-indicator">
            <span class="status-dot status-dot--{{ ollama_status }}"></span>
            <span style="color: var(--{{ 'success' if ollama_status == 'running' else 'error' }});">
                {{ t('system.' + ollama_status, lang) }}
            </span>
        </div>
    </div>
    <div class="system-actions">
        <button class="btn-sm btn-start"
                hx-post="/system/ollama/start"
                hx-target="#process-section"
                hx-swap="innerHTML"
                {% if ollama_status == 'running' or not installed %}disabled{% endif %}>
            {{ t('system.start', lang) }}
        </button>
        <button class="btn-sm btn-stop"
                hx-post="/system/ollama/stop"
                hx-target="#process-section"
                hx-swap="innerHTML"
                {% if ollama_status == 'stopped' %}disabled{% endif %}>
            {{ t('system.stop', lang) }}
        </button>
        <button class="btn-sm btn-restart"
                hx-post="/system/ollama/restart"
                hx-target="#process-section"
                hx-swap="innerHTML"
                {% if ollama_status == 'stopped' or not installed %}disabled{% endif %}>
            {{ t('system.restart', lang) }}
        </button>
    </div>
</div>
```

- [ ] **Step 4: Create `_model.html`**

```html
{% set lang = get_lang(request) %}
<div class="system-section">
    <div class="system-section-header">
        <div>
            <div class="system-section-title">{{ t('system.embedding_model', lang) }}</div>
            <div class="system-section-desc">{{ t('system.model_desc', lang) }}</div>
        </div>
    </div>
    <table class="data-table">
        <thead>
            <tr>
                <th>{{ t('system.model_name', lang) }}</th>
                <th>{{ t('system.model_size', lang) }}</th>
                <th>{{ t('system.model_status', lang) }}</th>
                <th style="text-align: right;">{{ t('system.model_action', lang) }}</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>{{ model_info.name }}</td>
                <td>{{ "%.1f GB"|format(model_info.size / 1e9) if model_info.size else '-' }}</td>
                <td>
                    {% if model_info.status == 'loaded' %}
                    <span class="status-ready">{{ t('system.model_loaded', lang) }}</span>
                    {% elif model_info.status == 'not_found' %}
                    <span class="status-accumulating">{{ t('system.model_not_found', lang) }}</span>
                    {% else %}
                    <span class="status-accumulating">{{ t('system.model_unavailable', lang) }}</span>
                    {% endif %}
                </td>
                <td style="text-align: right;">
                    {% if model_info.status == 'not_found' %}
                    <button class="btn-sm btn-pull"
                            hx-post="/system/model/pull"
                            hx-target="#model-section"
                            hx-swap="innerHTML"
                            hx-indicator="#global-indicator">
                        {{ t('system.pull', lang) }}
                    </button>
                    {% elif model_info.status == 'loaded' %}
                    <button class="btn-sm btn-delete"
                            hx-delete="/system/model/delete"
                            hx-target="#model-section"
                            hx-swap="innerHTML"
                            hx-confirm="Delete {{ model_info.name }}?">
                        {{ t('system.delete', lang) }}
                    </button>
                    {% endif %}
                </td>
            </tr>
        </tbody>
    </table>
</div>
```

- [ ] **Step 5: Create `_launchagent.html`**

```html
{% set lang = get_lang(request) %}
<div class="system-section">
    <div class="system-section-header">
        <div>
            <div class="system-section-title">{{ t('system.autostart', lang) }}</div>
            <div class="system-section-desc">{{ t('system.autostart_desc', lang) }}: {{ launchagent.path }}</div>
        </div>
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <button class="toggle-switch toggle-switch--{{ 'on' if launchagent.enabled else 'off' }}"
                    hx-post="/system/launchagent/toggle"
                    hx-target="#launchagent-section"
                    hx-swap="innerHTML">
            </button>
            <span style="font-size: 0.8125rem; font-weight: 500; color: var(--{{ 'success' if launchagent.enabled else 'text-dim' }});">
                {{ t('system.enabled' if launchagent.enabled else 'system.disabled', lang) }}
            </span>
        </div>
    </div>
</div>
```

- [ ] **Step 6: Commit**

```bash
git add src/cognitive_memory/dashboard/templates/system/
git commit -m "feat(dashboard): add system page templates with htmx"
```

---

### Task 8: Routes — System Page and htmx Endpoints

**Files:**
- Create: `src/cognitive_memory/dashboard/routes/system.py`
- Create: `tests/test_dashboard/test_system_routes.py`

- [ ] **Step 1: Write failing route tests**

```python
"""Route tests for /system."""

from __future__ import annotations

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from unittest.mock import patch, MagicMock

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.dashboard import create_app


class FakeOllamaHandler(BaseHTTPRequestHandler):
    models = [
        {"name": "zylonai/multilingual-e5-large:latest", "size": 1300000000,
         "modified_at": "2026-03-01T00:00:00Z"},
    ]

    def do_GET(self):
        if self.path == "/api/tags":
            body = json.dumps({"models": self.models}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def log_message(self, *args):
        pass


@pytest.fixture
def fake_ollama():
    server = HTTPServer(("127.0.0.1", 0), FakeOllamaHandler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture
def system_config(tmp_path, fake_ollama):
    (tmp_path / "cogmem.toml").write_text(
        f'[cogmem]\nembedding_model = "zylonai/multilingual-e5-large"\n'
        f'embedding_url = "{fake_ollama}/api/embed"\n',
        encoding="utf-8",
    )
    logs_dir = tmp_path / "memory" / "logs"
    logs_dir.mkdir(parents=True)
    return CogMemConfig.from_toml(tmp_path / "cogmem.toml")


@pytest.fixture
def system_client(system_config, fake_ollama):
    from starlette.testclient import TestClient
    with patch(
        "cognitive_memory.dashboard.services.ollama_service._DEFAULT_BASE_URL",
        fake_ollama,
    ):
        yield TestClient(create_app(system_config))


class TestSystemPage:
    def test_system_returns_200(self, system_client):
        resp = system_client.get("/system")
        assert resp.status_code == 200
        assert "System" in resp.text or "システム" in resp.text

    def test_system_shows_process_status(self, system_client):
        resp = system_client.get("/system")
        assert "Running" in resp.text or "起動中" in resp.text

    def test_system_shows_model_info(self, system_client):
        resp = system_client.get("/system")
        assert "multilingual-e5-large" in resp.text

    def test_system_shows_launchagent(self, system_client):
        resp = system_client.get("/system")
        assert "LaunchAgent" in resp.text or "自動起動" in resp.text


class TestSystemActions:
    @patch("cognitive_memory.dashboard.services.ollama_service.stop_serve")
    def test_stop_action(self, mock_stop, system_client):
        mock_stop.return_value = {"ok": True}
        resp = system_client.post("/system/ollama/stop")
        assert resp.status_code == 200
        mock_stop.assert_called_once()

    @patch("cognitive_memory.dashboard.services.ollama_service.start_serve")
    def test_start_action(self, mock_start, system_client):
        mock_start.return_value = {"ok": True}
        resp = system_client.post("/system/ollama/start")
        assert resp.status_code == 200
        mock_start.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_dashboard/test_system_routes.py -v`
Expected: ImportError or 404 — routes not registered

- [ ] **Step 3: Implement system routes**

```python
"""System management routes — Ollama process, model, and LaunchAgent."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..services import ollama_service

router = APIRouter()


def _base_url(request: Request) -> str:
    """Get Ollama base URL from config or default."""
    config = request.app.state.config
    # Derive base URL from embedding_url (strip /api/embed suffix)
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
```

- [ ] **Step 4: Register router in `app.py`**

Add to `app.py` after the existing router imports:

```python
from .routes.system import router as system_router
```

And register it:

```python
app.include_router(system_router, prefix="/system")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_dashboard/test_system_routes.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/cognitive_memory/dashboard/routes/system.py tests/test_dashboard/test_system_routes.py src/cognitive_memory/dashboard/app.py
git commit -m "feat(dashboard): add /system routes and htmx endpoints"
```

---

### Task 9: Sidebar — Add System Nav Link

**Files:**
- Modify: `src/cognitive_memory/dashboard/templates/base.html`

- [ ] **Step 1: Add System link to sidebar**

Add this link after the search link and before the `lang-switch` div in `base.html`:

```html
        <a href="/system" class="nav-link {% if active_page == 'system' %}active{% endif %}">
            <span class="nav-icon nav-icon-gear">&#9881;</span> <span class="nav-text">{{ t('nav.system', lang) }}</span>
        </a>
```

- [ ] **Step 2: Verify the nav link appears**

Run: `python -c "from starlette.testclient import TestClient; from cognitive_memory.config import CogMemConfig; from cognitive_memory.dashboard import create_app; c = CogMemConfig(); client = TestClient(create_app(c)); r = client.get('/'); assert '/system' in r.text; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/cognitive_memory/dashboard/templates/base.html
git commit -m "feat(dashboard): add System nav link to sidebar"
```

---

### Task 10: Overview Page — Ollama Stat Card

**Files:**
- Create: `src/cognitive_memory/dashboard/templates/memory/_ollama_card.html`
- Modify: `src/cognitive_memory/dashboard/routes/memory.py`
- Modify: `src/cognitive_memory/dashboard/templates/memory/overview.html`

- [ ] **Step 1: Create `_ollama_card.html` template fragment**

```html
{% set lang = get_lang(request) %}
<div class="stat-card">
    <div class="stat-label">Ollama</div>
    <div class="ollama-status">
        {% if ollama_status == 'running' and ollama_model.status == 'loaded' %}
        <span class="status-dot status-dot--running"></span>
        <span class="stat-value" style="font-size: 1.5rem;">{{ t('system.running', lang) }}</span>
        {% elif ollama_status == 'stopped' %}
        <span class="status-dot status-dot--stopped"></span>
        <span class="stat-value" style="font-size: 1.5rem;">{{ t('system.stopped', lang) }}</span>
        {% else %}
        <span class="status-dot status-dot--warning"></span>
        <span class="stat-value" style="font-size: 1.5rem;">{{ t('system.running', lang) }}</span>
        {% endif %}
    </div>
    <div class="stat-sub">
        {% if ollama_status == 'stopped' %}
        <span style="color: var(--error);">{{ t('system.embedding_unavailable', lang) }}</span>
        {% elif ollama_model.status == 'loaded' %}
        <span style="background: rgba(90,154,90,0.12); padding: 2px 8px; border-radius: 4px; color: var(--success);">
            {{ ollama_model.name }}
        </span>
        {% elif ollama_model.status == 'not_found' %}
        <span style="color: var(--warning);">
            {{ t('system.model_missing', lang) }} — <a href="/system" style="color: var(--warning); text-decoration: underline;">{{ t('system.pull_required', lang) }}</a>
        </span>
        {% endif %}
    </div>
</div>
```

- [ ] **Step 2: Modify `routes/memory.py` to pass Ollama status**

Add import and pass Ollama data to template:

```python
from ..services import ollama_service
```

In the `overview` function, add before the return:

```python
    ollama_status = ollama_service.get_status()
    ollama_model = ollama_service.check_embedding_model(config)
```

And add to the template context dict:

```python
    "ollama_status": ollama_status,
    "ollama_model": ollama_model,
```

- [ ] **Step 3: Modify `overview.html` to include the Ollama card**

Add this as the last card inside the `stats-grid` div (after the Categories stat-card):

```html
    {% include "memory/_ollama_card.html" %}
```

- [ ] **Step 4: Verify the card appears**

Run: `python -c "from starlette.testclient import TestClient; from cognitive_memory.config import CogMemConfig; from cognitive_memory.dashboard import create_app; c = CogMemConfig(); client = TestClient(create_app(c)); r = client.get('/'); assert 'Ollama' in r.text; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/cognitive_memory/dashboard/templates/memory/_ollama_card.html src/cognitive_memory/dashboard/routes/memory.py src/cognitive_memory/dashboard/templates/memory/overview.html
git commit -m "feat(dashboard): add Ollama status card to memory overview"
```

---

### Task 11: Run Full Test Suite

**Files:** None (verification only)

- [ ] **Step 1: Run all dashboard tests**

Run: `python -m pytest tests/test_dashboard/ -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 2: Run full project tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Manual verification — start dashboard and check pages**

Run: `cogmem dashboard --no-browser --port 8780` and verify:
1. Overview page shows Ollama stat-card
2. System page loads at `/system`
3. Sidebar shows System link

- [ ] **Step 4: Commit any test fixes if needed**
