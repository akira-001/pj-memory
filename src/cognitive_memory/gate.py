"""Adaptive search gate — skip trivial queries, force memory-related ones."""

from __future__ import annotations

import re
from typing import List, Optional

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


TOPIC_PATTERNS: List[str] = [
    r"(について|に関して|の件|どう思う|どうかな|どうなってる)",
    r"(what about|regarding|how about|let's discuss)",
    r"(設計|実装|分析|調査|検討|比較|評価|方針|戦略)",
]


def should_context_search(
    query: str, session_keywords: Optional[List[str]] = None
) -> bool:
    """Extended gate for context-aware search — includes topic patterns and session keywords."""
    if should_search(query):
        return True

    q = query.strip()
    if not q:
        return False

    for p in TOPIC_PATTERNS:
        if re.search(p, q, re.IGNORECASE):
            return True

    if session_keywords:
        q_lower = q.lower()
        for kw in session_keywords:
            if kw.lower() in q_lower:
                return True

    return False
