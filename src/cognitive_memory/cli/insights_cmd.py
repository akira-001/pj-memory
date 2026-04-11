"""cogmem insights — usage analytics."""
from __future__ import annotations

import json


def run_insights(days: int | None = None, json_output: bool = False) -> None:
    from ..config import CogMemConfig
    from ..insights import InsightsEngine

    config = CogMemConfig.find_and_load()
    engine = InsightsEngine(config)
    report = engine.generate(days=days)

    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    if report.get("empty"):
        print("No memories found.")
        return

    print(f"Total memories : {report['total_memories']}")
    print(f"Date range     : {report['date_range']['min']} — {report['date_range']['max']}")
    print(f"Avg arousal    : {report['avg_arousal']:.3f}")
    print()
    print("Arousal buckets:")
    for b in report["arousal_buckets"]:
        bar = "\u2588" * max(1, b["count"] // 2) if b["count"] > 0 else ""
        print(f"  {b['label']:8s}  {b['count']:4d}  {bar}")
    print()
    print("Category breakdown:")
    for cat, cnt in sorted(report["category_counts"].items(), key=lambda x: -x[1]):
        print(f"  {cat:12s}  {cnt}")
    if report["top_recalled"]:
        print()
        print("Top recalled memories:")
        for r in report["top_recalled"][:5]:
            snippet = r["content"].split("\n")[0][:80]
            print(f"  [{r['recall_count']}x] {r['date']}  {snippet}")
