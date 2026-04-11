"""InsightsEngine — usage analytics for Cognitive Memory.

Analyzes the memories SQLite database to produce:
- Total memories, avg arousal, date range
- Arousal bucket distribution
- Category breakdown
- Daily memory counts
- Top recalled memories
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import CogMemConfig

_CATEGORY_RE = re.compile(r"###\s+\[([A-Z_]+)\]", re.MULTILINE)


def _extract_category(content: str) -> str:
    """Extract the first category tag from a memory content string."""
    m = _CATEGORY_RE.search(content)
    return m.group(1) if m else "OTHER"


class InsightsEngine:
    """Analyze the memories database and return a structured report dict."""

    def __init__(self, config: CogMemConfig) -> None:
        self._config = config

    def generate(self, days: Optional[int] = None) -> Dict[str, Any]:
        """Generate insights report.

        Args:
            days: Optional lookback window in days. None = all time.

        Returns:
            dict with keys: empty, total_memories, avg_arousal, date_range,
            arousal_buckets, category_counts, daily_counts, top_recalled.
        """
        db_path = self._config.database_path
        if not Path(db_path).exists():
            return self._empty_report()

        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
        except sqlite3.Error:
            return self._empty_report()

        try:
            where = ""
            params: tuple = ()
            if days is not None:
                from datetime import datetime, timedelta

                cutoff = (datetime.now().date() - timedelta(days=days)).isoformat()
                where = "WHERE date >= ?"
                params = (cutoff,)

            row = conn.execute(
                f"SELECT COUNT(*) as cnt, MIN(date) as min_date, "
                f"MAX(date) as max_date, AVG(arousal) as avg_arousal "
                f"FROM memories {where}",
                params,
            ).fetchone()

            total = row["cnt"] or 0
            if total == 0:
                return self._empty_report()

            avg_arousal = round(row["avg_arousal"] or 0.0, 3)
            date_range = {"min": row["min_date"] or "", "max": row["max_date"] or ""}

            # Arousal buckets
            bucket_defs = [
                ("0.0\u20130.4", 0.0, 0.4),
                ("0.4\u20130.6", 0.4, 0.6),
                ("0.6\u20130.8", 0.6, 0.8),
                ("0.8\u20131.0", 0.8, 1.01),
            ]
            and_clause = "AND" if where else "WHERE"
            arousal_buckets: List[Dict[str, Any]] = []
            for label, lo, hi in bucket_defs:
                count = conn.execute(
                    f"SELECT COUNT(*) FROM memories {where} "
                    f"{and_clause} arousal >= ? AND arousal < ?",
                    params + (lo, hi),
                ).fetchone()[0]
                arousal_buckets.append({"label": label, "count": count})

            # Category counts
            rows = conn.execute(
                f"SELECT content FROM memories {where}", params
            ).fetchall()
            category_counts: Dict[str, int] = {}
            for r in rows:
                cat = _extract_category(r["content"])
                category_counts[cat] = category_counts.get(cat, 0) + 1

            # Daily counts
            daily_rows = conn.execute(
                f"SELECT date, COUNT(*) as count FROM memories {where} "
                f"GROUP BY date ORDER BY date",
                params,
            ).fetchall()
            daily_counts = [
                {"date": r["date"], "count": r["count"]} for r in daily_rows
            ]

            # Top recalled
            top_rows = conn.execute(
                f"SELECT content_hash, date, content, arousal, recall_count, last_recalled "
                f"FROM memories {where} "
                f"{and_clause} recall_count > 0 "
                f"ORDER BY recall_count DESC LIMIT 10",
                params,
            ).fetchall()
            top_recalled = [
                {
                    "content_hash": r["content_hash"],
                    "date": r["date"],
                    "content": r["content"][:120],
                    "arousal": r["arousal"],
                    "recall_count": r["recall_count"],
                    "last_recalled": r["last_recalled"],
                }
                for r in top_rows
            ]

            return {
                "empty": False,
                "total_memories": total,
                "avg_arousal": avg_arousal,
                "date_range": date_range,
                "arousal_buckets": arousal_buckets,
                "category_counts": dict(
                    sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
                ),
                "daily_counts": daily_counts,
                "top_recalled": top_recalled,
            }
        finally:
            conn.close()

    def _empty_report(self) -> Dict[str, Any]:
        return {
            "empty": True,
            "total_memories": 0,
            "avg_arousal": 0.0,
            "date_range": {"min": "", "max": ""},
            "arousal_buckets": [],
            "category_counts": {},
            "daily_counts": [],
            "top_recalled": [],
        }
