"""cogmem dashboard — web UI for cognitive memory."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import CogMemConfig

from .app import create_app

__all__ = ["create_app"]
