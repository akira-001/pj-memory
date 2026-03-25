"""Memory aggregation service for dashboard overview."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from ...config import CogMemConfig


def get_overview_data(config: CogMemConfig) -> dict[str, Any]:
    """Aggregate memory data for the overview page.

    Returns:
        {
            "total_memories": int,
            "date_range": {"min": str, "max": str},
            "avg_arousal": float,
            "daily_counts": [{"date": str, "count": int}, ...],
            "arousal_histogram": [{"bucket": str, "count": int}, ...],
            "category_counts": {"INSIGHT": N, "DECISION": N, ...},
        }
    """
    db_path = config.database_path
    if not Path(db_path).exists():
        return _empty_data()

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return _empty_data()

    try:
        # Basic stats
        row = conn.execute(
            "SELECT COUNT(*) as cnt, MIN(date) as min_date, "
            "MAX(date) as max_date, AVG(arousal) as avg_arousal "
            "FROM memories"
        ).fetchone()

        total = row["cnt"] or 0
        if total == 0:
            return _empty_data()

        date_range = {
            "min": row["min_date"] or "",
            "max": row["max_date"] or "",
        }
        avg_arousal = round(row["avg_arousal"] or 0.0, 2)

        # Daily counts
        daily_rows = conn.execute(
            "SELECT date, COUNT(*) as count FROM memories "
            "GROUP BY date ORDER BY date"
        ).fetchall()
        daily_counts = [{"date": r["date"], "count": r["count"]} for r in daily_rows]

        # Arousal histogram (bucket in Python)
        arousal_rows = conn.execute("SELECT arousal FROM memories").fetchall()
        buckets = [0] * 10
        for r in arousal_rows:
            val = r["arousal"]
            if val is not None:
                idx = min(int(val * 10), 9)
                buckets[idx] += 1

        arousal_histogram = [
            {"bucket": f"{i/10:.1f}-{(i+1)/10:.1f}", "count": buckets[i]}
            for i in range(10)
        ]

        # Category counts from content
        content_rows = conn.execute("SELECT content FROM memories").fetchall()
        category_counts: dict[str, int] = {}
        for r in content_rows:
            match = re.search(r"\[([A-Z]+)\]", r["content"] or "")
            if match:
                cat = match.group(1)
                category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "total_memories": total,
            "total_days": len(daily_counts),
            "date_range": date_range,
            "avg_arousal": avg_arousal,
            "daily_counts": daily_counts,
            "arousal_histogram": arousal_histogram,
            "category_counts": category_counts,
        }

    finally:
        conn.close()


def _empty_data() -> dict[str, Any]:
    """Return zero-value overview data for empty or missing DB."""
    return {
        "total_memories": 0,
        "total_days": 0,
        "date_range": {"min": "", "max": ""},
        "avg_arousal": 0.0,
        "daily_counts": [],
        "arousal_histogram": [
            {"bucket": f"{i/10:.1f}-{(i+1)/10:.1f}", "count": 0}
            for i in range(10)
        ],
        "category_counts": {},
    }


def get_memory_summary(config: CogMemConfig) -> dict:
    """Lightweight summary: just counts and daily distribution."""
    db_path = config.database_path
    if not Path(db_path).exists():
        return {"total_memories": 0, "total_days": 0, "daily_counts": []}
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        daily_rows = conn.execute(
            "SELECT date, COUNT(*) as count FROM memories GROUP BY date ORDER BY date"
        ).fetchall()
        daily_counts = [{"date": r["date"], "count": r["count"]} for r in daily_rows]
        return {"total_memories": total, "total_days": len(daily_counts), "daily_counts": daily_counts}
    except sqlite3.Error:
        return {"total_memories": 0, "total_days": 0, "daily_counts": []}
    finally:
        conn.close()
