"""Insights data service for dashboard."""
from __future__ import annotations

from typing import Any, Dict, Optional

from ...config import CogMemConfig
from ...insights import InsightsEngine


def get_insights_data(config: CogMemConfig, days: Optional[int] = None) -> Dict[str, Any]:
    """Return insights report dict for template rendering."""
    return InsightsEngine(config).generate(days=days)
