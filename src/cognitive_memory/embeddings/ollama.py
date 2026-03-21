"""Ollama embedding provider — zero external dependencies (urllib.request)."""

from __future__ import annotations

import json
import urllib.request
from typing import List, Optional


class OllamaEmbedding:
    """Embedding provider using Ollama's /api/embed endpoint."""

    def __init__(
        self,
        model: str = "zylonai/multilingual-e5-large",
        url: str = "http://localhost:11434/api/embed",
        timeout: int = 10,
    ):
        self.model = model
        self.url = url
        self.timeout = timeout

    def embed(self, text: str) -> Optional[List[float]]:
        """Embed a single text."""
        result = self.embed_batch([text])
        if result is None:
            return None
        return result[0]

    def embed_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Embed multiple texts via Ollama batch API."""
        try:
            data = json.dumps({"model": self.model, "input": texts}).encode()
            req = urllib.request.Request(
                self.url, data=data, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read())
            return result["embeddings"]
        except Exception:
            return None
