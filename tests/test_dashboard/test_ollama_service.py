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
