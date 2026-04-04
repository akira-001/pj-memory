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
        resp = system_client.get("/system/")
        assert resp.status_code == 200
        assert "System" in resp.text or "システム" in resp.text

    def test_system_shows_process_status(self, system_client):
        resp = system_client.get("/system/")
        assert "Running" in resp.text or "起動中" in resp.text

    def test_system_shows_model_info(self, system_client):
        resp = system_client.get("/system/")
        assert "multilingual-e5-large" in resp.text

    def test_system_shows_launchagent(self, system_client):
        resp = system_client.get("/system/")
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
