"""Size / bloat health check for knowledge summary.md.

summary.md is @-referenced from CLAUDE.md and loaded in full every session,
so unbounded growth translates directly into fixed token cost. This module
gives wrap a mechanical signal to prune: file size against a configured
threshold, and the number of accumulated ``*[prior]*`` session-summary
blocks against a configured cap.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from .config import CogMemConfig

# A prior session summary block is conventionally marked with "*[prior]*"
# (wrap demotes the previous session's summary with this marker). Matched
# case-insensitively, tolerating optional whitespace inside the brackets.
_PRIOR_MARKER = re.compile(r"\*\[\s*prior\s*\]\*", re.IGNORECASE)


@dataclass
class SummaryHealth:
    """Result of a summary.md health check."""

    exists: bool = False
    size_kb: float = 0.0
    max_kb: int = 0
    prior_count: int = 0
    prior_cap: int = 0
    warnings: List[str] = field(default_factory=list)

    @property
    def needs_pruning(self) -> bool:
        return bool(self.warnings)

    def to_dict(self) -> dict:
        return {
            "exists": self.exists,
            "size_kb": self.size_kb,
            "max_kb": self.max_kb,
            "prior_count": self.prior_count,
            "prior_cap": self.prior_cap,
            "needs_pruning": self.needs_pruning,
            "warnings": self.warnings,
        }


def check_summary_health(config: CogMemConfig) -> SummaryHealth:
    """Check knowledge summary.md size and prior-block accumulation.

    A ``summary_max_kb`` of 0 disables the size check.
    """
    path = config.knowledge_summary_path
    health = SummaryHealth(
        max_kb=config.summary_max_kb,
        prior_cap=config.summary_prior_sessions,
    )

    if not path.is_file():
        return health

    health.exists = True
    try:
        size_bytes = path.stat().st_size
        text = path.read_text(encoding="utf-8")
    except OSError:
        return health

    health.size_kb = round(size_bytes / 1024, 1)
    health.prior_count = len(_PRIOR_MARKER.findall(text))

    if config.summary_max_kb > 0 and health.size_kb > config.summary_max_kb:
        health.warnings.append(
            f"summary.md is {health.size_kb}KB (> {config.summary_max_kb}KB limit). "
            "Prune: rescue un-archived knowledge to insights.md / error-patterns.md, "
            "then delete old *[prior]* blocks and stale sections."
        )
    if health.prior_count > config.summary_prior_sessions:
        health.warnings.append(
            f"summary.md holds {health.prior_count} *[prior]* session summaries "
            f"(cap: {config.summary_prior_sessions}). Session summaries belong in "
            "memory/logs/ — delete the excess blocks."
        )

    return health
