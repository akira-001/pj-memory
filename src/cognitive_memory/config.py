"""Configuration management for Cognitive Memory."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

_DEFAULTS = {
    "logs_dir": "memory/logs",
    "db_path": "memory/vectors.db",
    "handover_delimiter": "## 引き継ぎ",
    "sim_weight": 0.7,
    "arousal_weight": 0.3,
    "base_half_life": 60.0,
    "decay_floor": 0.3,
    "embedding_provider": "ollama",
    "embedding_model": "zylonai/multilingual-e5-large",
    "embedding_url": "http://localhost:11434/api/embed",
    "embedding_timeout": 10,
}


@dataclass
class CogMemConfig:
    """Cognitive Memory configuration."""

    logs_dir: str = _DEFAULTS["logs_dir"]
    db_path: str = _DEFAULTS["db_path"]
    handover_delimiter: str = _DEFAULTS["handover_delimiter"]

    # Scoring
    sim_weight: float = _DEFAULTS["sim_weight"]
    arousal_weight: float = _DEFAULTS["arousal_weight"]
    base_half_life: float = _DEFAULTS["base_half_life"]
    decay_floor: float = _DEFAULTS["decay_floor"]

    # Embedding
    embedding_provider: str = _DEFAULTS["embedding_provider"]
    embedding_model: str = _DEFAULTS["embedding_model"]
    embedding_url: str = _DEFAULTS["embedding_url"]
    embedding_timeout: int = _DEFAULTS["embedding_timeout"]

    # Resolved base directory (set by from_toml / find_and_load)
    _base_dir: str = field(default=".", repr=False)

    @property
    def logs_path(self) -> Path:
        p = Path(self.logs_dir)
        if p.is_absolute():
            return p
        return Path(self._base_dir) / self.logs_dir

    @property
    def database_path(self) -> Path:
        p = Path(self.db_path)
        if p.is_absolute():
            return p
        return Path(self._base_dir) / self.db_path

    @classmethod
    def from_toml(cls, path: str | Path) -> CogMemConfig:
        """Load config from a TOML file."""
        if tomllib is None:
            raise ImportError(
                "tomli is required for Python < 3.11. "
                "Install with: pip install cognitive-memory"
            )
        p = Path(path)
        with open(p, "rb") as f:
            data = tomllib.load(f)

        section = data.get("cogmem", {})
        scoring = section.get("scoring", {})
        embedding = section.get("embedding", {})

        return cls(
            logs_dir=section.get("logs_dir", _DEFAULTS["logs_dir"]),
            db_path=section.get("db_path", _DEFAULTS["db_path"]),
            handover_delimiter=section.get(
                "handover_delimiter", _DEFAULTS["handover_delimiter"]
            ),
            sim_weight=scoring.get("sim_weight", _DEFAULTS["sim_weight"]),
            arousal_weight=scoring.get("arousal_weight", _DEFAULTS["arousal_weight"]),
            base_half_life=scoring.get("base_half_life", _DEFAULTS["base_half_life"]),
            decay_floor=scoring.get("decay_floor", _DEFAULTS["decay_floor"]),
            embedding_provider=embedding.get(
                "provider", _DEFAULTS["embedding_provider"]
            ),
            embedding_model=embedding.get("model", _DEFAULTS["embedding_model"]),
            embedding_url=embedding.get("url", _DEFAULTS["embedding_url"]),
            embedding_timeout=embedding.get(
                "timeout", _DEFAULTS["embedding_timeout"]
            ),
            _base_dir=str(p.parent),
        )

    @classmethod
    def find_and_load(cls, start_dir: Optional[str | Path] = None) -> CogMemConfig:
        """Search for cogmem.toml from start_dir upward. Falls back to env var or defaults."""
        env_path = os.environ.get("COGMEM_CONFIG")
        if env_path:
            return cls.from_toml(env_path)

        d = Path(start_dir) if start_dir else Path.cwd()
        while True:
            candidate = d / "cogmem.toml"
            if candidate.exists():
                return cls.from_toml(candidate)
            parent = d.parent
            if parent == d:
                break
            d = parent

        return cls()
