"""Adaptive search gate — skip trivial queries, force memory-related ones."""

from __future__ import annotations

import re
from typing import List

SKIP_PATTERNS: List[str] = [
    r"^(おはよう?|こんにちは|おつかれ|ありがとう|OK|了解|はい|うん)",
    r"^/",  # slash commands
    r"^(yes|no|ok|sure|thanks)",
]

FORCE_PATTERNS: List[str] = [
    r"(以前|前に|前回|あの時|覚えて|思い出)",
    r"(remember|previously|last time|before)",
]


def should_search(query: str) -> bool:
    """Adaptive gate: determine whether a query warrants memory search."""
    q = query.strip()
    if not q:
        return False

    for p in FORCE_PATTERNS:
        if re.search(p, q, re.IGNORECASE):
            return True

    for p in SKIP_PATTERNS:
        if re.search(p, q, re.IGNORECASE):
            return False

    cjk_count = len(re.findall(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]", q))
    if cjk_count > 0:
        return len(q) >= 6
    return len(q) >= 15
