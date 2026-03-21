"""Crystallization signal detection."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import List

from .config import CogMemConfig
from .parser import parse_entries


@dataclass
class CrystallizationSignals:
    """Result of crystallization signal check."""

    pattern_count: int = 0
    error_count: int = 0
    log_days: int = 0
    days_since_checkpoint: int = 0
    should_crystallize: bool = False
    triggered_conditions: List[str] = field(default_factory=list)

    # Thresholds used (for JSON output)
    pattern_threshold: int = 3
    error_threshold: int = 5
    log_days_threshold: int = 10
    checkpoint_interval_days: int = 21

    def to_dict(self) -> dict:
        """Serialize to a plain dict for JSON output."""
        return {
            "should_crystallize": self.should_crystallize,
            "pattern_count": self.pattern_count,
            "error_count": self.error_count,
            "log_days": self.log_days,
            "days_since_checkpoint": self.days_since_checkpoint,
            "triggered_conditions": self.triggered_conditions,
            "conditions": {
                "pattern_threshold": self.pattern_threshold,
                "error_threshold": self.error_threshold,
                "log_days_threshold": self.log_days_threshold,
                "checkpoint_interval_days": self.checkpoint_interval_days,
            },
        }


def check_signals(config: CogMemConfig) -> CrystallizationSignals:
    """Scan logs and check crystallization signal conditions."""
    logs_path = config.logs_path
    category_counter: Counter = Counter()
    log_dates: set = set()

    if logs_path.is_dir():
        for f in sorted(logs_path.iterdir()):
            if not f.name.endswith(".md"):
                continue
            if f.name.endswith(".compact.md"):
                continue

            # Extract date from filename (YYYY-MM-DD.md)
            date_str = f.stem  # e.g. "2026-03-21"
            log_dates.add(date_str)

            try:
                md_text = f.read_text(encoding="utf-8")
            except OSError:
                continue

            for entry in parse_entries(md_text, date_str, config.handover_delimiter):
                if entry.category:
                    category_counter[entry.category] += 1

    # Calculate days since last checkpoint
    try:
        last_cp = datetime.strptime(config.last_checkpoint, "%Y-%m-%d").date()
        days_since = (date.today() - last_cp).days
    except (ValueError, TypeError):
        days_since = 9999  # Never checkpointed

    # Build result
    signals = CrystallizationSignals(
        pattern_count=category_counter.get("PATTERN", 0),
        error_count=category_counter.get("ERROR", 0),
        log_days=len(log_dates),
        days_since_checkpoint=days_since,
        pattern_threshold=config.pattern_threshold,
        error_threshold=config.error_threshold,
        log_days_threshold=config.log_days_threshold,
        checkpoint_interval_days=config.checkpoint_interval_days,
    )

    # Check conditions
    triggered: List[str] = []

    if signals.pattern_count >= config.pattern_threshold:
        triggered.append(
            f"[PATTERN] entries: {signals.pattern_count} >= {config.pattern_threshold}"
        )
    if signals.error_count >= config.error_threshold:
        triggered.append(
            f"[ERROR] entries: {signals.error_count} >= {config.error_threshold}"
        )
    if signals.log_days >= config.log_days_threshold:
        triggered.append(
            f"Log days: {signals.log_days} >= {config.log_days_threshold}"
        )
    if signals.days_since_checkpoint >= config.checkpoint_interval_days:
        triggered.append(
            f"Days since checkpoint: {signals.days_since_checkpoint} >= {config.checkpoint_interval_days}"
        )

    signals.triggered_conditions = triggered
    signals.should_crystallize = len(triggered) > 0

    return signals
