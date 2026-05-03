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
    """Keyword search over raw log files (grep-equivalent).

    Two-pass strategy:
      1. Entry-level: parse_entries で得た [TYPE] エントリ単位でマッチ。
         既存の content_hash 紐付けと arousal 維持。
      2. Uncovered-line rescue: parse_entries が拾えなかった行（エントリ境界外の
         地の文）を救済。マッチ行の前後3行を context として返す。これで parser の
         取りこぼし（subsection、説明文、bullet 等）も検索可能になる。
    """
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
        parsed = list(parse_entries(md_text, date, config.handover_delimiter))

        # Pass 1: entry-level grep
        matched_contents: set = set()
        for entry in parsed:
            if any(k.lower() in entry.content.lower() for k in keywords):
                # Reverse lookup content_hash from DB
                found_hash = None
                if db_conn is not None:
                    try:
                        row = db_conn.execute(
                            "SELECT content_hash FROM memories WHERE content = ? AND date = ?",
                            (entry.content, date),
                        ).fetchone()
                        if row:
                            found_hash = row["content_hash"]
                    except sqlite3.Error:
                        pass
                decay = time_decay(
                    date,
                    entry.arousal,
                    base_half_life=config.base_half_life,
                    floor=config.decay_floor,
                )
                score = config.arousal_weight * entry.arousal * decay
                results.append(
                    SearchResult(
                        score=round(score, 4),
                        date=date,
                        content=entry.content,
                        arousal=entry.arousal,
                        source="grep",
                        content_hash=found_hash,
                    )
                )
                matched_contents.add(entry.content)

        # Pass 2: rescue lines that parse_entries did NOT cover
        # parser miss patterns: subsections, free text between entries, etc.
        covered_text = "\n".join(e.content for e in parsed)
        lines = md_text.split("\n")
        seen_ctx: set = set()
        for line_idx, line in enumerate(lines):
            if not any(k.lower() in line.lower() for k in keywords):
                continue
            stripped = line.strip()
            if not stripped:
                continue
            # Already covered by an entry → skip
            if stripped and stripped in covered_text:
                continue
            # Build ±3 line context
            start = max(0, line_idx - 3)
            end = min(len(lines), line_idx + 4)
            ctx = "\n".join(lines[start:end]).strip()
            if not ctx or ctx in seen_ctx or ctx in matched_contents:
                continue
            seen_ctx.add(ctx)
            # Use default arousal (0.5) for uncovered lines — no entry header
            uncovered_arousal = 0.5
            decay = time_decay(
                date,
                uncovered_arousal,
                base_half_life=config.base_half_life,
                floor=config.decay_floor,
            )
            # Penalize uncovered context slightly so entry-level matches rank higher
            score = config.arousal_weight * uncovered_arousal * decay * 0.7
            results.append(
                SearchResult(
                    score=round(score, 4),
                    date=date,
                    content=ctx,
                    arousal=uncovered_arousal,
                    source="grep_uncovered",
                    content_hash=None,
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
    """Merge grep and semantic results with quota guarantee + dedup.

    Score systems differ between semantic (cosine 0–1) and grep (arousal*decay,
    typically 0.05–0.3). Pure score sort lets semantic always win, hiding grep
    matches that are exact-keyword hits. To preserve recall on short keyword
    queries, reserve at least ⌈top_k/3⌉ slots for grep results (esp. uncovered
    rescue lines that the parser missed).
    """
    seen: set = set()
    merged: List[SearchResult] = []

    # Build set of semantic content keys so we can prefer semantic over a
    # duplicate grep hit (semantic carries cosine context).
    sem_keys = {r.content[:100] for r in semantic_results}

    grep_quota = max(1, top_k // 3) if grep_results else 0

    # 1. Reserve top grep slots first (especially grep_uncovered which won't
    #    survive a pure score sort against semantic results). Skip grep entries
    #    that duplicate a semantic result — the semantic version takes priority.
    for r in grep_results[:grep_quota]:
        key = r.content[:100]
        if key in sem_keys or key in seen:
            continue
        seen.add(key)
        merged.append(r)

    # 2. Fill remaining slots from combined pool, semantic-first dedup.
    pool = semantic_results + grep_results[grep_quota:]
    pool.sort(key=lambda x: x.score, reverse=True)
    for r in pool:
        if len(merged) >= top_k:
            break
        key = r.content[:100]
        if key not in seen:
            seen.add(key)
            merged.append(r)

    return merged[:top_k]
