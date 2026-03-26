"""cogmem recall-stats — show recall statistics."""

from __future__ import annotations

import json
import sys

from ..config import CogMemConfig
from ..store import MemoryStore


def run_recall_stats(json_output: bool = False):
    config = CogMemConfig.find_and_load()

    with MemoryStore(config) as store:
        try:
            rows = store.conn.execute(
                "SELECT content, recall_count, last_recalled, arousal, date "
                "FROM memories WHERE recall_count > 0 "
                "ORDER BY recall_count DESC LIMIT 10"
            ).fetchall()
        except Exception:
            rows = []

    if not rows:
        print("No recalled memories yet.")
        return

    if json_output:
        data = [
            {
                "title": r["content"].split("\n")[0][:80],
                "recall_count": r["recall_count"],
                "last_recalled": r["last_recalled"],
                "arousal": r["arousal"],
                "date": r["date"],
            }
            for r in rows
        ]
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"{'Recalls':>8}  {'Arousal':>7}  {'Date':>10}  Title")
        print("-" * 70)
        for r in rows:
            title = r["content"].split("\n")[0][:50]
            print(f"{r['recall_count']:>8}  {r['arousal']:>7.2f}  {r['date']:>10}  {title}")
