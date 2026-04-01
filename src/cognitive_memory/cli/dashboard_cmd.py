"""cogmem dashboard — start the web dashboard."""

from __future__ import annotations

import sys


def run_dashboard(host: str = "0.0.0.0", port: int = 8765, no_browser: bool = False):
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        print("Dashboard requires extras: pip install cogmem-agent[dashboard]")
        sys.exit(1)

    from ..config import CogMemConfig
    from ..dashboard import create_app

    config = CogMemConfig.find_and_load()
    app = create_app(config)

    if not no_browser:
        import threading
        import webbrowser
        threading.Timer(1.0, webbrowser.open, args=[f"http://{host}:{port}"]).start()

    print(f"Starting cogmem dashboard at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
