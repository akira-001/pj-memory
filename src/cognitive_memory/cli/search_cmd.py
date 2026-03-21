"""cogmem search — search memories."""

from __future__ import annotations

import json
from dataclasses import asdict

from ..config import CogMemConfig
from ..store import MemoryStore


def run_search(query: str, top_k: int = 5, json_output: bool = False):
    config = CogMemConfig.find_and_load()

    with MemoryStore(config) as store:
        response = store.search(query, top_k)

    if json_output:
        out = {
            "results": [asdict(r) for r in response.results],
            "status": response.status,
        }
        print(json.dumps(out, ensure_ascii=False))
    else:
        print(f"Status: {response.status}")
        print(f"Results: {len(response.results)}")
        print()
        for i, r in enumerate(response.results, 1):
            print(
                f"--- [{i}] score={r.score} date={r.date} "
                f"arousal={r.arousal} source={r.source} ---"
            )
            lines = r.content.split("\n")[:3]
            for line in lines:
                print(f"  {line}")
            print()
