"""MemoryStore — unified interface for indexing and searching memories."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .config import CogMemConfig
from .gate import should_search
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
                vector       BLOB
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
        """Index all log files in the configured logs directory."""
        logs_dir = self.config.logs_path
        if not logs_dir.exists():
            return 0

        files = sorted(logs_dir.glob("*.md"))
        files = [f for f in files if not f.name.endswith(".compact.md")]

        total = 0
        for fp in files:
            n = self.index_file(fp, force=force)
            if n > 0:
                print(f"  {fp.name}: {n} entries", file=sys.stderr)
            total += n
        return total

    def search(self, query: str, top_k: int = 5) -> SearchResponse:
        """Full search pipeline: gate → semantic+grep → merge. FailOpen on embed failure."""
        if not should_search(query):
            return SearchResponse(status="skipped_by_gate")

        # Try semantic search
        query_vec = self.embedder.embed(query)
        if query_vec is not None:
            sem_results, sem_status = semantic_search(
                query_vec, self.config.database_path, self.config, top_k
            )
            if sem_status == "ok":
                grep_results = grep_search(
                    query, self.config.logs_path, self.config, top_k
                )
                merged = merge_and_dedup(grep_results, sem_results, top_k)
                return SearchResponse(results=merged, status="ok")
            # Semantic partially failed (no_index, db_error) — fall through to grep
            status_reason = sem_status
        else:
            status_reason = "ollama_unavailable"

        # failOpen: fall back to grep
        grep_results = grep_search(query, self.config.logs_path, self.config, top_k)
        return SearchResponse(
            results=grep_results, status=f"degraded ({status_reason})"
        )

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
