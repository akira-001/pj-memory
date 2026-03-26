"""Integration tests for 3-stage memory pipeline:
   鮮明 (vivid) → 薄れる (fading) → 定着 (crystallized)
   + recall reinforcement across stages.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.parser import parse_entries
from cognitive_memory.store import MemoryStore

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def pipeline_store(tmp_path):
    """Store with a realistic session log indexed."""
    logs_dir = tmp_path / "memory" / "logs"
    logs_dir.mkdir(parents=True)

    fixture = FIXTURE_DIR / "session_auth_debug.md"
    log_file = logs_dir / "2026-03-20.md"
    log_file.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    (tmp_path / "cogmem.toml").write_text(
        '[cogmem]\nlogs_dir = "memory/logs"\ndb_path = "memory/vectors.db"\n'
        '[cogmem.crystallization]\npattern_threshold = 1\nerror_threshold = 1\n',
        encoding="utf-8",
    )
    config = CogMemConfig.from_toml(tmp_path / "cogmem.toml")

    with MemoryStore(config) as s:
        class DummyEmbedder:
            def embed(self, text):
                return [0.1] * 384
            def embed_batch(self, texts):
                return [[0.1 + i * 0.01] * 384 for i in range(len(texts))]
        s._embedder = DummyEmbedder()
        s.index_file(log_file, force=True)
        yield s


class TestStage1Vivid:
    """鮮明（直近）: 全エントリが保持され、arousal が正しい。"""

    def test_all_entries_indexed(self, pipeline_store):
        rows = pipeline_store.conn.execute(
            "SELECT COUNT(*) as n FROM memories WHERE date = '2026-03-20'"
        ).fetchone()
        assert rows["n"] == 9  # 8 entries + 1 SUMMARY

    def test_arousal_distribution(self, pipeline_store):
        rows = pipeline_store.conn.execute(
            "SELECT arousal FROM memories WHERE date = '2026-03-20' ORDER BY id"
        ).fetchall()
        arousals = [r["arousal"] for r in rows]
        assert arousals == pytest.approx([0.5, 0.4, 0.5, 0.8, 0.9, 0.5, 0.6, 0.8, 0.5])

    def test_categories_correct(self, pipeline_store):
        rows = pipeline_store.conn.execute(
            "SELECT content FROM memories WHERE date = '2026-03-20' ORDER BY id"
        ).fetchall()
        categories = []
        for r in rows:
            m = re.search(r"\[([A-Z]+)\]", r["content"])
            categories.append(m.group(1) if m else None)
        assert categories == [
            "SUMMARY",
            "QUESTION", "DECISION", "ERROR", "INSIGHT",
            "MILESTONE", "DECISION", "PATTERN", "MILESTONE",
        ]

    def test_high_arousal_entries_have_detail(self, pipeline_store):
        rows = pipeline_store.conn.execute(
            "SELECT content, arousal FROM memories "
            "WHERE date = '2026-03-20' AND arousal >= 0.8 ORDER BY id"
        ).fetchall()
        assert len(rows) == 3
        for r in rows:
            lines = r["content"].strip().split("\n")
            assert len(lines) >= 3, f"High arousal entry should have detail: {lines[0]}"


class TestStage2Fading:
    """薄れる（compact化）: 高 arousal のみ残る。"""

    def test_compact_preserves_high_arousal(self, pipeline_store):
        rows = pipeline_store.conn.execute(
            "SELECT content, arousal FROM memories "
            "WHERE date = '2026-03-20' AND arousal >= 0.6 ORDER BY arousal DESC"
        ).fetchall()
        assert len(rows) == 4
        assert rows[0]["arousal"] == 0.9

    def test_low_arousal_would_be_dropped(self, pipeline_store):
        rows = pipeline_store.conn.execute(
            "SELECT content, arousal FROM memories "
            "WHERE date = '2026-03-20' AND arousal < 0.6"
        ).fetchall()
        assert len(rows) == 5  # 4 entries + 1 SUMMARY (arousal 0.5)
        for r in rows:
            assert r["arousal"] < 0.6


class TestStage3Crystallized:
    """定着（結晶化）: パターンが抽象ルールに変換される。"""

    def test_signals_detect_patterns(self, pipeline_store):
        from cognitive_memory.signals import check_signals
        signals = check_signals(pipeline_store.config)
        assert signals.pattern_count >= 1
        assert signals.error_count >= 1

    def test_error_pattern_extractable(self, pipeline_store):
        row = pipeline_store.conn.execute(
            "SELECT content FROM memories "
            "WHERE date = '2026-03-20' AND arousal = 0.8 "
            "AND content LIKE '%ERROR%'"
        ).fetchone()
        assert row is not None
        content = row["content"]
        assert "仮説" in content

    def test_pattern_entry_is_abstractable(self, pipeline_store):
        row = pipeline_store.conn.execute(
            "SELECT content FROM memories "
            "WHERE date = '2026-03-20' AND content LIKE '%PATTERN%'"
        ).fetchone()
        assert row is not None
        content = row["content"]
        assert "datetime.now()" in content or "タイムゾーン" in content
        assert "禁止" in content or "ルール" in content


class TestRecallReinforcement:
    """想起による arousal 変化の検証。"""

    def test_never_recalled_stays_same(self, pipeline_store):
        row = pipeline_store.conn.execute(
            "SELECT arousal, recall_count FROM memories "
            "WHERE date = '2026-03-20' AND arousal = 0.4"
        ).fetchone()
        assert row["recall_count"] == 0
        assert row["arousal"] == pytest.approx(0.4)

    def test_single_recall_boosts(self, pipeline_store):
        row = pipeline_store.conn.execute(
            "SELECT content_hash, arousal FROM memories "
            "WHERE date = '2026-03-20' AND arousal = 0.5 LIMIT 1"
        ).fetchone()
        original_arousal = row["arousal"]
        pipeline_store.reinforce_recall(row["content_hash"])
        updated = pipeline_store.conn.execute(
            "SELECT arousal, recall_count FROM memories WHERE content_hash = ?",
            (row["content_hash"],),
        ).fetchone()
        assert updated["recall_count"] == 1
        assert updated["arousal"] == pytest.approx(original_arousal + 0.1)

    def test_repeated_recalls_accumulate(self, pipeline_store):
        row = pipeline_store.conn.execute(
            "SELECT content_hash FROM memories "
            "WHERE date = '2026-03-20' AND arousal = 0.6 LIMIT 1"
        ).fetchone()
        for _ in range(3):
            pipeline_store.reinforce_recall(row["content_hash"])
        updated = pipeline_store.conn.execute(
            "SELECT arousal, recall_count FROM memories WHERE content_hash = ?",
            (row["content_hash"],),
        ).fetchone()
        assert updated["recall_count"] == 3
        assert updated["arousal"] == pytest.approx(0.9)

    def test_arousal_cap_on_high_entry(self, pipeline_store):
        row = pipeline_store.conn.execute(
            "SELECT content_hash FROM memories "
            "WHERE date = '2026-03-20' AND arousal = 0.9 LIMIT 1"
        ).fetchone()
        pipeline_store.reinforce_recall(row["content_hash"])
        pipeline_store.reinforce_recall(row["content_hash"])
        updated = pipeline_store.conn.execute(
            "SELECT arousal, recall_count FROM memories WHERE content_hash = ?",
            (row["content_hash"],),
        ).fetchone()
        assert updated["recall_count"] == 2
        assert updated["arousal"] == pytest.approx(1.0)

    def test_recall_promotes_low_to_survival(self, pipeline_store):
        """A low-arousal entry (0.4) recalled 3 times reaches 0.7,
        crossing the compact survival threshold (0.6)."""
        row = pipeline_store.conn.execute(
            "SELECT content_hash FROM memories "
            "WHERE date = '2026-03-20' AND arousal = 0.4 LIMIT 1"
        ).fetchone()
        for _ in range(3):
            pipeline_store.reinforce_recall(row["content_hash"])
        updated = pipeline_store.conn.execute(
            "SELECT arousal FROM memories WHERE content_hash = ?",
            (row["content_hash"],),
        ).fetchone()
        assert updated["arousal"] == pytest.approx(0.7)
        assert updated["arousal"] >= 0.6


class TestLLMAbstractionQuality:
    """LLM を使って結晶化の抽象度を評価する。
    MLX サーバーが起動していない環境ではスキップ。"""

    _MLX_URL = "http://localhost:8080/v1/chat/completions"
    _MLX_MODEL = "mlx-community/Qwen3-32B-4bit"

    @pytest.fixture(autouse=True)
    def check_llm(self):
        import urllib.request
        try:
            resp = urllib.request.urlopen("http://localhost:8080/v1/models", timeout=3)
            data = json.loads(resp.read())
            models = [m.get("id", "") for m in data.get("data", [])]
            if self._MLX_MODEL not in models:
                pytest.skip(f"{self._MLX_MODEL} not available on MLX server")
        except Exception:
            pytest.skip("MLX server not available")

    def _generate(self, prompt: str, retries: int = 2) -> str:
        import urllib.request
        import urllib.error
        payload = json.dumps({
            "model": self._MLX_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
            "temperature": 0.1,
        }).encode()
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(
                    self._MLX_URL,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                resp = urllib.request.urlopen(req, timeout=120)
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"].strip()
            except (urllib.error.URLError, OSError):
                if attempt == retries:
                    pytest.skip("MLX generation timed out")
        return ""

    def test_pattern_abstracts_to_rule(self, pipeline_store):
        row = pipeline_store.conn.execute(
            "SELECT content FROM memories "
            "WHERE date = '2026-03-20' AND content LIKE '%PATTERN%'"
        ).fetchone()

        prompt = (
            "以下のログエントリから、再利用可能な抽象ルールを1行で抽出してください。\n\n"
            f"{row['content']}\n\nルール:"
        )
        result = self._generate(prompt)
        assert any(
            kw in result for kw in ["タイムゾーン", "timezone", "UTC", "datetime", "時刻"]
        ), f"LLM rule should mention timezone concept, got: {result}"
        assert len(result) < 200, f"Rule too long ({len(result)} chars): {result}"

    def test_error_abstracts_to_lesson(self, pipeline_store):
        row = pipeline_store.conn.execute(
            "SELECT content FROM memories "
            "WHERE date = '2026-03-20' AND content LIKE '%ERROR%'"
        ).fetchone()

        prompt = (
            "以下のエラーログから、次回同じ状況を避けるための教訓を1行で抽出してください。\n\n"
            f"{row['content']}\n\n教訓:"
        )
        result = self._generate(prompt)
        assert any(
            kw in result for kw in ["仮説", "検証", "確認", "先に", "hypothesis", "verify"]
        ), f"LLM lesson should mention verification, got: {result}"
        assert len(result) < 200, f"Lesson too long ({len(result)} chars): {result}"
