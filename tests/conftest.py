"""Shared fixtures for Cognitive Memory tests."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from typing import List, Optional

import pytest

from cognitive_memory.config import CogMemConfig


class MockEmbedder:
    """Deterministic mock embedder for testing."""

    def __init__(self, dim: int = 4):
        self.dim = dim
        self._call_count = 0

    def embed(self, text: str) -> Optional[List[float]]:
        """Return a deterministic vector based on text hash."""
        h = hash(text) % 1000
        vec = [(h + i) / 1000.0 for i in range(self.dim)]
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        self._call_count += 1
        return vec

    def embed_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Embed multiple texts."""
        return [self.embed(t) for t in texts]


class FailingEmbedder:
    """Embedder that always fails."""

    def embed(self, text: str) -> Optional[List[float]]:
        return None

    def embed_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        return None


@pytest.fixture
def mock_embedder():
    return MockEmbedder()


@pytest.fixture
def failing_embedder():
    return FailingEmbedder()


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_vectors.db"


@pytest.fixture
def sample_log():
    return """# 2026-03-21 セッションログ

## セッション概要
テスト用

## ログエントリ

### [INSIGHT][TECH] テスト洞察エントリ
*Arousal: 0.7 | Emotion: Clarity*
これはテスト用の洞察エントリ。十分な長さが必要なので長めに書く。

---

### [DECISION][TECH] テスト決定エントリ
*Arousal: 0.6 | Emotion: Determination*
これはテスト用の決定エントリ。十分な長さが必要なので長めに書く。

---

### [MILESTONE][TECH] テストマイルストーン
*Arousal: 0.8 | Emotion: Relief*
これはテスト用のマイルストーンエントリ。十分な長さが必要。

---

## 引き継ぎ
- この内容は検索対象外
- 引き継ぎのテスト
"""


@pytest.fixture
def sample_log_file(tmp_path, sample_log):
    fp = tmp_path / "memory" / "logs" / "2026-03-21.md"
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(sample_log, encoding="utf-8")
    return fp


@pytest.fixture
def config_with_tmp(tmp_path, sample_log_file):
    logs_dir = tmp_path / "memory" / "logs"
    db_path = tmp_path / "memory" / "vectors.db"
    return CogMemConfig(
        logs_dir=str(logs_dir),
        db_path=str(db_path),
        _base_dir="",
    )
