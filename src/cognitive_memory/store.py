"""MemoryStore — unified interface for indexing and searching memories."""

from __future__ import annotations

import hashlib
import threading
import json
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .config import CogMemConfig
from .context import SearchCache, filter_flashbacks
from .gate import should_context_search, should_search
from .parser import parse_entries
from .scoring import normalize
from .search import grep_search, merge_and_dedup, semantic_search
from .types import MemoryEntry, SearchResponse, SearchResult


class MemoryStore:
    """Main interface for Cognitive Memory: index logs and search memories."""

    def __init__(
        self,
        config: Optional[CogMemConfig] = None,
        embedder: Optional[object] = None,
    ):
        self.config = config or CogMemConfig()
        self._embedder = embedder
        self._conn: Optional[sqlite3.Connection] = None

        # Background prefetch
        self._prefetch_result: Optional["SearchResponse"] = None
        self._prefetch_lock = threading.Lock()
        self._prefetch_thread: Optional[threading.Thread] = None

    def __enter__(self):
        self._init_db()
        return self

    def __exit__(self, *args):
        self.close()

    @property
    def embedder(self):
        if self._embedder is None:
            from .embeddings.ollama import OllamaEmbedding

            self._embedder = OllamaEmbedding(
                model=self.config.embedding_model,
                url=self.config.embedding_url,
                timeout=self.config.embedding_timeout,
            )
        return self._embedder

    def _init_db(self):
        """Initialize SQLite database and tables."""
        db_path = self.config.database_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id           INTEGER PRIMARY KEY,
                content_hash TEXT UNIQUE,
                date         TEXT,
                content      TEXT,
                arousal      REAL,
                vector       BLOB,
                recall_count INTEGER DEFAULT 0,
                last_recalled TEXT
            )
        """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS indexed_files (
                filename     TEXT PRIMARY KEY,
                indexed_at   TEXT,
                entry_count  INTEGER
            )
        """
        )
        # Migration for existing DBs
        for col, col_def in [
            ("recall_count", "INTEGER DEFAULT 0"),
            ("last_recalled", "TEXT"),
        ]:
            try:
                self._conn.execute(f"ALTER TABLE memories ADD COLUMN {col} {col_def}")
            except sqlite3.OperationalError:
                pass  # column already exists
        self._conn.commit()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._init_db()
        return self._conn

    def close(self):
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def reinforce_recall(self, content_hash: str, arousal_boost: float = 0.1) -> None:
        """Record a recall event: increment count, boost arousal, update timestamp."""
        self.conn.execute(
            """
            UPDATE memories
            SET recall_count = recall_count + 1,
                last_recalled = ?,
                arousal = MIN(arousal + ?, 1.0)
            WHERE content_hash = ?
            """,
            (datetime.now().isoformat(), arousal_boost, content_hash),
        )
        self.conn.commit()

    def index_file(self, filepath: Path, force: bool = False) -> int:
        """Index a single log file. Returns number of entries stored."""
        filename = filepath.name
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", filename)
        if not date_match:
            return 0
        date = date_match.group(1)

        if not force:
            row = self.conn.execute(
                "SELECT indexed_at FROM indexed_files WHERE filename = ?", (filename,)
            ).fetchone()
            if row:
                indexed_at = datetime.fromisoformat(row["indexed_at"])
                file_mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                if file_mtime <= indexed_at:
                    return 0

        md_text = filepath.read_text(encoding="utf-8")
        entries = list(
            parse_entries(md_text, date, self.config.handover_delimiter)
        )

        if not entries:
            self.conn.execute(
                "INSERT OR REPLACE INTO indexed_files (filename, indexed_at, entry_count) VALUES (?, ?, ?)",
                (filename, datetime.now().isoformat(), 0),
            )
            self.conn.commit()
            return 0

        texts = [e.content for e in entries]

        # Remove stale entries for this date whose content_hash is no longer present
        new_hashes = {hashlib.sha256(e.content.encode()).hexdigest() for e in entries}
        existing = self.conn.execute(
            "SELECT content_hash FROM memories WHERE date = ?", (date,)
        ).fetchall()
        stale = [row["content_hash"] for row in existing if row["content_hash"] not in new_hashes]
        if stale:
            self.conn.executemany(
                "DELETE FROM memories WHERE content_hash = ?",
                [(h,) for h in stale],
            )
            print(f"  [CLEANUP] {filename}: removed {len(stale)} stale entr{'y' if len(stale) == 1 else 'ies'}", file=sys.stderr)

        vectors = self.embedder.embed_batch(texts)
        if vectors is None:
            print(f"  [SKIP] {filename}: embed failed", file=sys.stderr)
            return 0

        stored = 0
        for entry, vec in zip(entries, vectors):
            content_hash = hashlib.sha256(entry.content.encode()).hexdigest()
            vec_normalized = normalize(vec)
            try:
                self.conn.execute(
                    "INSERT OR IGNORE INTO memories (content_hash, date, content, arousal, vector) VALUES (?, ?, ?, ?, ?)",
                    (
                        content_hash,
                        entry.date,
                        entry.content,
                        entry.arousal,
                        json.dumps(vec_normalized),
                    ),
                )
                stored += 1
            except sqlite3.Error as e:
                print(f"  [ERROR] SQLite write failed: {e}", file=sys.stderr)

        self.conn.execute(
            "INSERT OR REPLACE INTO indexed_files (filename, indexed_at, entry_count) VALUES (?, ?, ?)",
            (filename, datetime.now().isoformat(), stored),
        )
        self.conn.commit()
        return stored

    def index_dir(self, force: bool = False) -> int:
        """Index all log files across configured logs paths (per-user + root)."""
        # Collect *.md from all configured paths, dedup by absolute path so
        # overlapping per-user/root scopes don't index the same file twice.
        all_files: list[Path] = []
        seen_files: set = set()
        for logs_dir in self.config.logs_paths:
            if not logs_dir.exists():
                continue
            for fp in logs_dir.glob("*.md"):
                key = fp.resolve()
                if key in seen_files:
                    continue
                seen_files.add(key)
                all_files.append(fp)
        if not all_files:
            return 0

        files = sorted(all_files)
        # Prefer original .md over .compact.md; use compact only when
        # the original has 0 indexed entries (e.g. old format logs).
        regular = {f.stem: f for f in files if not f.name.endswith(".compact.md")}
        compact = {
            f.name.replace(".compact.md", ""): f
            for f in files
            if f.name.endswith(".compact.md")
        }

        selected: list[Path] = []
        all_dates = sorted(set(list(regular.keys()) + list(compact.keys())))
        for date_key in all_dates:
            reg = regular.get(date_key)
            comp = compact.get(date_key)
            if reg:
                # Check if regular file already indexed with 0 entries
                row = self.conn.execute(
                    "SELECT entry_count FROM indexed_files WHERE filename = ?",
                    (reg.name,),
                ).fetchone()
                if row and row["entry_count"] == 0 and comp:
                    # Regular had no entries; try compact instead
                    selected.append(comp)
                else:
                    selected.append(reg)
            elif comp:
                selected.append(comp)
        files = selected

        total = 0
        for fp in files:
            n = self.index_file(fp, force=force)
            if n > 0:
                print(f"  {fp.name}: {n} entries", file=sys.stderr)
            total += n
        return total

    def _reinforce_results(self, results: List[SearchResult]) -> None:
        """Reinforce recall for search results that have a content_hash."""
        for result in results:
            if result.content_hash is not None:
                self.reinforce_recall(result.content_hash)

    def _grep_all_paths(self, query: str, top_k: int) -> List[SearchResult]:
        """grep across all configured logs paths (per-user + root)."""
        seen_files: set = set()
        all_results: List[SearchResult] = []
        for logs_dir in self.config.logs_paths:
            # Avoid re-scanning the same file when paths overlap
            if logs_dir in seen_files:
                continue
            seen_files.add(logs_dir)
            results = grep_search(query, logs_dir, self.config, top_k)
            all_results.extend(results)
        # Dedup by content prefix (same entry might surface from overlapping dirs)
        seen_content: set = set()
        deduped: List[SearchResult] = []
        all_results.sort(key=lambda x: x.score, reverse=True)
        for r in all_results:
            key = r.content[:100]
            if key in seen_content:
                continue
            seen_content.add(key)
            deduped.append(r)
        return deduped[:top_k]

    def _execute_search(self, query: str, top_k: int = 5) -> SearchResponse:
        """Core search pipeline: semantic+grep → merge. FailOpen on embed failure.

        Does NOT apply the search gate — callers are responsible for gating.
        """
        # Try semantic search
        query_vec = self.embedder.embed(query)
        if query_vec is not None:
            sem_results, sem_status = semantic_search(
                query_vec, self.config.database_path, self.config, top_k
            )
            if sem_status == "ok":
                grep_results = self._grep_all_paths(query, top_k)
                merged = merge_and_dedup(grep_results, sem_results, top_k)
                return SearchResponse(results=merged, status="ok")
            # Semantic partially failed (no_index, db_error) — fall through to grep
            status_reason = sem_status
        else:
            status_reason = "ollama_unavailable"

        # failOpen: fall back to grep
        grep_results = self._grep_all_paths(query, top_k)
        return SearchResponse(
            results=grep_results, status=f"degraded ({status_reason})"
        )

    def search(self, query: str, top_k: int = 5) -> SearchResponse:
        """Full search pipeline with gate check and recall reinforcement."""
        if not should_search(query):
            return SearchResponse(status="skipped_by_gate")
        response = self._execute_search(query, top_k)
        self._reinforce_results(response.results)
        return response

    def context_search(
        self,
        query: str,
        cache: Optional[SearchCache] = None,
        session_keywords: Optional[List[str]] = None,
        top_k: int = 3,
    ) -> SearchResponse:
        """Context-aware search with caching and flashback filtering.

        Args:
            query: Search query string.
            cache: Optional session-scoped SearchCache. Create with
                ``SearchCache(config.context_cache_max_size,
                config.context_cache_sim_threshold)``.
                If None, caching is skipped for this call. Pass a persistent
                cache object across calls to benefit from cross-call deduplication.
            session_keywords: Optional keywords that force the gate to pass
                even for short or low-entropy queries.
            top_k: Maximum results to return before flashback filtering.
        """
        # 1. Disabled check
        if not self.config.context_search_enabled:
            return SearchResponse(status="disabled")

        # 2. Gate check
        if not should_context_search(query, session_keywords):
            return SearchResponse(status="skipped_by_gate")

        # 3. Consume background prefetch if available
        prefetched = self.pop_prefetch_result()
        if prefetched is not None:
            filtered = filter_flashbacks(
                prefetched.results,
                self.config.context_flashback_sim,
                self.config.context_flashback_arousal,
            )
            filtered_response = SearchResponse(
                results=filtered[:top_k],
                status=prefetched.status + " (prefetched)",
            )
            if cache is not None:
                query_vec = self.embedder.embed(query)
                if query_vec is not None:
                    cache.put(query_vec, filtered_response)
            self._reinforce_results(filtered_response.results)
            return filtered_response

        # 4. Cache check (requires embedding for similarity comparison)
        query_vec = self.embedder.embed(query)
        if query_vec is not None and cache is not None:
            cached = cache.get(query_vec)
            if cached is not None:
                status = cached.status
                if "(cached)" not in status:
                    status = status + " (cached)"
                return SearchResponse(results=cached.results, status=status)

        # 5. Full search pipeline (bypass search() gate since we already gated above)
        response = self._execute_search(query, top_k)

        # 6. Apply flashback filtering
        filtered = filter_flashbacks(
            response.results,
            self.config.context_flashback_sim,
            self.config.context_flashback_arousal,
        )

        filtered_response = SearchResponse(results=filtered, status=response.status)

        # 7. Store in cache
        if cache is not None and query_vec is not None:
            cache.put(query_vec, filtered_response)

        # 8. Reinforce recall for returned results
        self._reinforce_results(filtered_response.results)

        # 9. Return
        return filtered_response

    def queue_prefetch(self, query: str) -> None:
        """Queue a background search for the next call.

        Runs _execute_search in a daemon thread. The result is stored in
        _prefetch_result and consumed by pop_prefetch_result().
        If a prefetch is already in flight, it is cancelled (result discarded).
        """
        def _run(q: str) -> None:
            try:
                result = self._execute_search(q, top_k=self.config.context_cache_max_size)
                with self._prefetch_lock:
                    self._prefetch_result = result
            except Exception:
                pass  # Non-fatal: next real search will run synchronously

        with self._prefetch_lock:
            self._prefetch_result = None  # clear stale result
            self._prefetch_thread = None  # reset before new thread starts

        t = threading.Thread(target=_run, args=(query,), daemon=True)
        self._prefetch_thread = t
        t.start()

    def pop_prefetch_result(self) -> Optional["SearchResponse"]:
        """Consume and return the prefetched result, or None if not ready."""
        with self._prefetch_lock:
            result = self._prefetch_result
            self._prefetch_result = None
            return result

    def status(self) -> dict:
        """Return index statistics."""
        db_path = self.config.database_path
        if not db_path.exists():
            return {"indexed_files": 0, "total_entries": 0, "db_size_bytes": 0}

        total_entries = self.conn.execute(
            "SELECT COUNT(*) FROM memories"
        ).fetchone()[0]
        indexed_files = self.conn.execute(
            "SELECT COUNT(*) FROM indexed_files"
        ).fetchone()[0]
        db_size = db_path.stat().st_size

        return {
            "indexed_files": indexed_files,
            "total_entries": total_entries,
            "db_size_bytes": db_size,
        }
