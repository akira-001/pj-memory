"""cogmem signals — check crystallization signals."""

from __future__ import annotations

import json
import sys


def run_signals():
    """Check crystallization signals and output JSON."""
    from ..config import CogMemConfig
    from ..signals import check_signals

    try:
        config = CogMemConfig.find_and_load()
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)

    result = check_signals(config)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
