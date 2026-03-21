"""Core data types for Cognitive Memory."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MemoryEntry:
    """A single parsed log entry."""

    date: str
    content: str
    arousal: float = 0.5
    category: Optional[str] = None


@dataclass
class SearchResult:
    """A single search result with scoring metadata."""

    score: float
    date: str
    content: str
    arousal: float
    source: str  # "semantic" | "grep"
    cosine_sim: Optional[float] = None
    time_decay: Optional[float] = None


@dataclass
class SearchResponse:
    """Aggregated search response."""

    results: List[SearchResult] = field(default_factory=list)
    status: str = "ok"  # "ok" | "skipped_by_gate" | "degraded (reason)" | ...
