"""Search functions: semantic search, grep search, merge & dedup."""

from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

from .config import CogMemConfig
from .parser import parse_entries
from .scoring import cosine_sim, normalize, time_decay
from .types import SearchResult


def semantic_search(
    query_vec: List[float],
    db_path: Path,
    config: CogMemConfig,
    top_k: int = 5,
) -> Tuple[List[SearchResult], str]:
    """Semantic search over indexed memories. Returns (results, status)."""
    if not db_path.exists():
        return [], "no_index"

    query_vec = normalize(query_vec)

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return [], "db_error"

    t0 = time.time()
    results: List[SearchResult] = []
    try:
        for row in conn.execute(
            "SELECT content_hash, date, content, arousal, vector FROM memories"
        ):
            v = json.loads(row["vector"])
            sim = cosine_sim(query_vec, v)
            decay = time_decay(
                row["date"],
                row["arousal"],
                base_half_life=config.base_half_life,
                floor=config.decay_floor,
            )
            score = (config.sim_weight * sim + config.arousal_weight * row["arousal"]) * decay
            results.append(
                SearchResult(
                    score=round(score, 4),
                    date=row["date"],
                    content=row["content"],
                    arousal=row["arousal"],
                    source="semantic",
                    cosine_sim=round(sim, 4),
                    time_decay=round(decay, 4),
                    content_hash=row["content_hash"],
                )
            )
    except sqlite3.Error:
        conn.close()
        return [], "db_error"

    elapsed = time.time() - t0
    print(
        f"[semantic] {len(results)} entries scanned in {elapsed:.3f}s",
        file=sys.stderr,
    )

    conn.close()
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:top_k], "ok"


def grep_search(
    query: str,
    logs_dir: Path,
    config: CogMemConfig,
    top_k: int = 5,
) -> List[SearchResult]:
    """Keyword search over raw log files (grep-equivalent)."""
    results: List[SearchResult] = []
    keywords = [k.strip() for k in query.split() if k.strip()]
    if not keywords:
        return []

    if not logs_dir.exists():
        return []

    # DB connection for content_hash reverse lookup
    db_conn = None
    db_path = config.database_path
    if db_path.exists():
        try:
            db_conn = sqlite3.connect(str(db_path))
            db_conn.row_factory = sqlite3.Row
        except sqlite3.Error:
            db_conn = None

    for fp in sorted(logs_dir.glob("*.md")):
        if fp.name.endswith(".compact.md"):
            continue
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", fp.name)
        if not date_match:
            continue
        date = date_match.group(1)

        md_text = fp.read_text(encoding="utf-8")
        content = md_text.split(config.handover_delimiter)[0]
        entries = re.split(r"\n(?=### )", content)

        for e in entries:
            if not e.strip() or not e.startswith("###"):
                continue
            e_lower = e.lower()
            if any(k.lower() in e_lower for k in keywords):
                m = re.search(r"Arousal: ([0-9.]+)", e)
                try:
                    arousal = float(m.group(1)) if m else 0.5
                except (ValueError, AttributeError):
                    arousal = 0.5
                e_clean = e.replace("---", "").strip()
                # Reverse lookup content_hash from DB
                found_hash = None
                if db_conn is not None:
                    try:
                        row = db_conn.execute(
                            "SELECT content_hash FROM memories WHERE content = ? AND date = ?",
                            (e_clean, date),
                        ).fetchone()
                        if row:
                            found_hash = row["content_hash"]
                    except sqlite3.Error:
                        pass
                decay = time_decay(
                    date,
                    arousal,
                    base_half_life=config.base_half_life,
                    floor=config.decay_floor,
                )
                score = config.arousal_weight * arousal * decay
                results.append(
                    SearchResult(
                        score=round(score, 4),
                        date=date,
                        content=e_clean,
                        arousal=arousal,
                        source="grep",
                        content_hash=found_hash,
                    )
                )

    if db_conn is not None:
        db_conn.close()

    results.sort(key=lambda x: x.score, reverse=True)
    return results[:top_k]


def merge_and_dedup(
    grep_results: List[SearchResult],
    semantic_results: List[SearchResult],
    top_k: int = 5,
) -> List[SearchResult]:
    """Merge grep and semantic results, dedup by content prefix."""
    seen: set = set()
    merged: List[SearchResult] = []

    # semantic results have priority
    for r in semantic_results + grep_results:
        key = r.content[:100]
        if key not in seen:
            seen.add(key)
            merged.append(r)

    merged.sort(key=lambda x: x.score, reverse=True)
    return merged[:top_k]
