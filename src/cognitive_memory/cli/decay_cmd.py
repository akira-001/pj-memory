"""cogmem decay — apply memory decay to consolidated logs."""
from __future__ import annotations

import json
import sys


def run_decay(dry_run: bool = False, json_output: bool = False):
    """Load config, call apply_decay, print results."""
    from ..config import CogMemConfig
    from ..decay import apply_decay

    try:
        config = CogMemConfig.find_and_load()
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)

    if not config.decay_enabled:
        msg = "Decay is disabled in config (decay.enabled = false)"
        if json_output:
            print(json.dumps({"status": "disabled", "message": msg}))
        else:
            print(msg)
        return

    result = apply_decay(config, dry_run=dry_run)

    if json_output:
        result["dry_run"] = dry_run
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        mode = " (dry run)" if dry_run else ""
        print(f"Memory decay{mode}:")
        print(f"  Kept (vivid/active): {result['kept']}")
        print(f"  Compacted:           {result['compacted']}")
        print(f"  Skipped:             {result['skipped']}")
