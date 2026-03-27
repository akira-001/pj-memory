"""Memory decay logic — human-like forgetting mechanism."""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum


class DecayAction(Enum):
    KEEP = "keep"        # 詳細を残す（鮮烈な記憶 or 活発に想起）
    COMPACT = "compact"  # compact に圧縮して詳細削除
    DELETE = "delete"     # 詳細削除（compact 済みなら何もしない）


def evaluate_entry(
    arousal: float,
    recall_count: int,
    last_recalled: str | None,
    arousal_threshold: float = 0.7,
    recall_threshold: int = 2,
    recall_window_months: int = 18,
) -> DecayAction:
    """Evaluate whether a memory entry should be kept, compacted, or deleted.

    Rules (modeled after human memory):
    1. High arousal → always keep (vivid memories persist)
    2. Frequently recalled AND recently recalled → keep (active memories)
    3. Frequently recalled BUT not recalled in window → delete (faded memories)
    4. Everything else → compact (mundane events lose detail, keep gist)
    """
    # Rule 1: Vivid memories persist
    if arousal >= arousal_threshold:
        return DecayAction.KEEP

    # Rule 2 & 3: Recall-based retention
    if recall_count >= recall_threshold:
        if last_recalled is None:
            return DecayAction.DELETE
        last_dt = datetime.fromisoformat(last_recalled)
        window = datetime.now() - timedelta(days=recall_window_months * 30)
        if last_dt >= window:
            return DecayAction.KEEP
        return DecayAction.DELETE

    # Rule 4: Mundane memories → compact
    return DecayAction.COMPACT
