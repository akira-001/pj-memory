"""Log entry parser and noise filter."""

from __future__ import annotations

import re
from typing import Iterator, List

from .types import MemoryEntry

NOISE_PATTERNS: List[str] = [
    r"^(了解|OK|はい|うん|おはよう)",
    r"情報がありません",
    r"覚えていますか",
]
MIN_CONTENT_LENGTH = 20


def is_noise(content: str) -> bool:
    """Check if content is noise (too short or matches noise patterns)."""
    if len(content.strip()) < MIN_CONTENT_LENGTH:
        return True
    for p in NOISE_PATTERNS:
        if re.search(p, content):
            return True
    return False


def parse_entries(
    md_text: str,
    date: str,
    handover_delimiter: str = "## 引き継ぎ",
) -> Iterator[MemoryEntry]:
    """Extract log entries from a markdown file, excluding handover section."""
    content = md_text.split(handover_delimiter)[0]
    entries = re.split(r"\n(?=### )", content)
    for e in entries:
        if not e.strip() or not e.startswith("###"):
            continue
        e_clean = e.replace("---", "").strip()
        if is_noise(e_clean):
            continue
        m = re.search(r"Arousal: ([0-9.]+)", e_clean)
        try:
            arousal = float(m.group(1)) if m else 0.5
        except (ValueError, AttributeError):
            arousal = 0.5
        # Extract category from header like ### [INSIGHT][TECH] or ### [INSIGHT]
        cat_match = re.search(r"\[([A-Z]+)\]", e_clean)
        category = cat_match.group(1) if cat_match else None
        yield MemoryEntry(date=date, content=e_clean, arousal=arousal, category=category)
