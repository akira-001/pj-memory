"""cogmem context-search — context-aware memory search."""

from __future__ import annotations

import json
from dataclasses import asdict

from ..config import CogMemConfig
from ..store import MemoryStore


def run_context_search(
    query: str,
    top_k: int = 3,
    json_output: bool = False,
    keywords: list[str] | None = None,
):
    config = CogMemConfig.find_and_load()

    with MemoryStore(config) as store:
        response = store.context_search(query, session_keywords=keywords, top_k=top_k)

    if json_output:
        out = {
            "results": [asdict(r) for r in response.results],
            "status": response.status,
        }
        print(json.dumps(out, ensure_ascii=False))
    else:
        fenced = response.format_fenced()
        if fenced:
            print(fenced)
        else:
            print(f"[cogmem] status={response.status} results=0")
