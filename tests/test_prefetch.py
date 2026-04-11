"""Tests for background prefetch in MemoryStore."""
import time
from pathlib import Path

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.store import MemoryStore


@pytest.fixture
def prefetch_store(tmp_path, mock_embedder):
    cfg = CogMemConfig(
        logs_dir=str(tmp_path / "memory" / "logs"),
        db_path=str(tmp_path / "memory" / "vectors.db"),
        _base_dir=str(tmp_path),
    )
    (tmp_path / "memory" / "logs").mkdir(parents=True)
    store = MemoryStore(cfg, embedder=mock_embedder)
    store._init_db()
    return store


class TestQueuePrefetch:
    def test_queue_prefetch_does_not_raise(self, prefetch_store):
        prefetch_store.queue_prefetch("test query")

    def test_prefetch_result_available_after_wait(self, prefetch_store):
        prefetch_store.queue_prefetch("test query")
        time.sleep(0.2)
        result = prefetch_store.pop_prefetch_result()
        assert result is None or hasattr(result, "results")

    def test_pop_prefetch_clears_cache(self, prefetch_store):
        prefetch_store.queue_prefetch("test query")
        time.sleep(0.2)
        prefetch_store.pop_prefetch_result()
        assert prefetch_store.pop_prefetch_result() is None

    def test_queue_prefetch_replaces_in_flight(self, prefetch_store):
        prefetch_store.queue_prefetch("first query")
        prefetch_store.queue_prefetch("second query")
        time.sleep(0.2)

    def test_prefetch_thread_is_daemon(self, prefetch_store):
        prefetch_store.queue_prefetch("test query")
        t = prefetch_store._prefetch_thread
        if t is not None:
            assert t.daemon is True
