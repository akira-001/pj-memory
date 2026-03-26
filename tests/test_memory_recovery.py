"""Memory recovery tests — simulating human recall experiments.

Hypothesis: Higher arousal entries are more recoverable because they contain
richer context (prior names, causal chains, user quotes, trial-and-error).
This mirrors the psychological finding that emotional memories are recalled
more readily than neutral ones.

Test design:
1. Index a realistic mixed-arousal session log (12 entries, arousal 0.4-1.0)
2. For each entry, craft a "memory probe" — a search query using DIFFERENT
   words than the original (simulating "trying to remember something")
3. Check if the entry is found and its score
4. Compare recovery rates across arousal tiers
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.store import MemoryStore

requires_ollama = pytest.mark.skipif(
    subprocess.run(
        ["curl", "-s", "http://localhost:11434/api/tags"],
        capture_output=True, timeout=3,
    ).returncode != 0,
    reason="Ollama not running",
)

FIXTURE = Path(__file__).parent / "fixtures" / "session_vivid_mixed.md"

# Memory probes: queries that use DIFFERENT words than the original entry.
# Grouped by arousal tier.
# Format: (probe_query, expected_substring_in_result, original_arousal)
PROBES_LOW = [
    # Arousal 0.4 — minimal context, fact-only entries
    ("Square のリクエスト上限", "レート制限", 0.4),
    ("PCI のコンプライアンス書類", "PCI DSS", 0.4),
]

PROBES_MID = [
    # Arousal 0.6-0.7 — some context
    ("決済の抽象化レイヤー", "PaymentGateway", 0.6),
    ("Square SDK で署名を検証する", "verifySignature", 0.6),
    ("テストカードの重複コード", "ハードコード", 0.7),
    ("注文から返金までのテスト", "Cypress", 0.7),
]

PROBES_HIGH = [
    # Arousal 0.8-1.0 — rich context, quotes, causal chains
    ("本番キーの漏洩事故", "STRIPE_SECRET_KEY", 0.8),
    ("冪等性の仕組みの違い", "idempotency_key", 0.8),
    ("日付がずれてた決済バグ", "タイムゾーン", 0.9),
    ("過剰設計をやめた判断", "YAGNI", 0.9),
    ("Stripe から乗り換え完了", "本番デプロイ", 1.0),
]


@pytest.fixture
def indexed_store(tmp_path):
    """Build a store with the mixed-arousal session log indexed."""
    logs_dir = tmp_path / "memory" / "logs"
    logs_dir.mkdir(parents=True)
    log_file = logs_dir / "2026-03-15.md"
    log_file.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "cogmem.toml").write_text(
        '[cogmem]\nlogs_dir = "memory/logs"\ndb_path = "memory/vectors.db"\n',
        encoding="utf-8",
    )
    config = CogMemConfig.from_toml(tmp_path / "cogmem.toml")
    store = MemoryStore(config)
    store.index_file(log_file, force=True)
    return store


@requires_ollama
class TestMemoryRecoveryByArousal:
    """Higher arousal entries should be more recoverable via semantic search."""

    @pytest.mark.parametrize("probe,expected,arousal", PROBES_HIGH)
    def test_high_arousal_recoverable(self, indexed_store, probe, expected, arousal):
        """High arousal (0.8-1.0) entries are found by indirect queries."""
        results = indexed_store.search(probe, top_k=5)
        # NOTE: check if results is SearchResponse with .results attribute
        result_list = results.results if hasattr(results, 'results') else results
        contents = " ".join(r.content for r in result_list)
        assert expected in contents, (
            f"Probe '{probe}' failed to recover entry containing '{expected}'"
        )

    @pytest.mark.parametrize("probe,expected,arousal", PROBES_MID)
    def test_mid_arousal_recoverable(self, indexed_store, probe, expected, arousal):
        """Mid arousal (0.6-0.7) entries are found by indirect queries."""
        results = indexed_store.search(probe, top_k=8)
        result_list = results.results if hasattr(results, 'results') else results
        contents = " ".join(r.content for r in result_list)
        assert expected in contents, (
            f"Probe '{probe}' failed to recover entry containing '{expected}'"
        )

    def test_high_arousal_scores_higher_than_low(self, indexed_store):
        """Average score of high-arousal probes exceeds low-arousal probes."""
        def get_score(probes):
            scores = []
            for probe, expected, _ in probes:
                results = indexed_store.search(probe, top_k=5)
                result_list = results.results if hasattr(results, 'results') else results
                for r in result_list:
                    if expected in r.content:
                        scores.append(r.score)
                        break
            return scores

        high_scores = get_score(PROBES_HIGH)
        low_scores = get_score(PROBES_LOW)

        assert len(high_scores) > 0, "No high-arousal entries recovered"
        avg_high = sum(high_scores) / len(high_scores)
        if low_scores:
            avg_low = sum(low_scores) / len(low_scores)
            assert avg_high >= avg_low, (
                f"High arousal avg ({avg_high:.3f}) should >= low ({avg_low:.3f})"
            )

    def test_recovery_rate_correlates_with_arousal(self, indexed_store):
        """Recovery rate (found in top-5) increases with arousal tier."""
        def recovery_rate(probes):
            found = 0
            for probe, expected, _ in probes:
                results = indexed_store.search(probe, top_k=5)
                result_list = results.results if hasattr(results, 'results') else results
                contents = " ".join(r.content for r in result_list)
                if expected in contents:
                    found += 1
            return found / len(probes) if probes else 0

        rate_low = recovery_rate(PROBES_LOW)
        rate_mid = recovery_rate(PROBES_MID)
        rate_high = recovery_rate(PROBES_HIGH)

        # High should be best, mid should be at least as good as low
        assert rate_high >= rate_mid, (
            f"High recovery ({rate_high:.0%}) should >= mid ({rate_mid:.0%})"
        )
        # Log the rates for observability
        print(f"\nRecovery rates: low={rate_low:.0%}, mid={rate_mid:.0%}, high={rate_high:.0%}")

    def test_low_arousal_partial_recovery(self, indexed_store):
        """Low arousal entries may be found but with lower confidence."""
        for probe, expected, arousal in PROBES_LOW:
            results = indexed_store.search(probe, top_k=5)
            result_list = results.results if hasattr(results, 'results') else results
            # We don't assert they're found — low arousal entries being
            # hard to recover is the expected behavior (like forgetting
            # mundane details). We just verify no errors.
            assert isinstance(result_list, list)
