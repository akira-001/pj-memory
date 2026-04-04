"""Tests for ollama_service — status and model queries."""

from __future__ import annotations

import json
import signal
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread
from unittest.mock import patch, MagicMock

import pytest

from cognitive_memory.dashboard.services.ollama_service import (
    get_status,
    get_models,
    check_embedding_model,
    is_ollama_installed,
    start_serve,
    stop_serve,
    pull_model,
    delete_model,
    get_launchagent_status,
    set_launchagent,
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
        pass


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


# ---------------------------------------------------------------------------
# Task 2: Process Control
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Task 3: Model Pull / Delete
# ---------------------------------------------------------------------------


class FakeOllamaPullDeleteHandler(BaseHTTPRequestHandler):
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


# ---------------------------------------------------------------------------
# Task 4: LaunchAgent Management
# ---------------------------------------------------------------------------


class TestLaunchAgent:
    def test_status_no_plist(self, tmp_path):
        fake_path = tmp_path / "com.ollama.serve.plist"
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
