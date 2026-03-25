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
    # Identity
    "identity_soul": "identity/soul.md",
    "identity_user": "identity/user.md",
    # Knowledge
    "knowledge_summary": "memory/knowledge/summary.md",
    "knowledge_error_patterns": "memory/knowledge/error-patterns.md",
    # Session
    "contexts_dir": "memory/contexts",
    "recent_logs": 2,
    "prefer_compact": True,
    "token_budget": 6000,
    # Crystallization
    "pattern_threshold": 3,
    "error_threshold": 5,
    "log_days_threshold": 10,
    "checkpoint_interval_days": 21,
    "last_checkpoint": "",
    "checkpoint_count": 0,
    # Context Search
    "context_search_enabled": True,
    "context_flashback_sim": 0.65,
    "context_flashback_arousal": 0.5,
    "context_cache_max_size": 20,
    "context_cache_sim_threshold": 0.9,
    # Metrics
    "total_sessions": 0,
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

    # Identity paths (relative to base_dir)
    identity_soul: str = _DEFAULTS["identity_soul"]
    identity_user: str = _DEFAULTS["identity_user"]

    # Knowledge paths
    knowledge_summary: str = _DEFAULTS["knowledge_summary"]
    knowledge_error_patterns: str = _DEFAULTS["knowledge_error_patterns"]

    # Session
    contexts_dir: str = _DEFAULTS["contexts_dir"]
    recent_logs: int = _DEFAULTS["recent_logs"]
    prefer_compact: bool = _DEFAULTS["prefer_compact"]
    token_budget: int = _DEFAULTS["token_budget"]

    # Crystallization
    pattern_threshold: int = _DEFAULTS["pattern_threshold"]
    error_threshold: int = _DEFAULTS["error_threshold"]
    log_days_threshold: int = _DEFAULTS["log_days_threshold"]
    checkpoint_interval_days: int = _DEFAULTS["checkpoint_interval_days"]
    last_checkpoint: str = _DEFAULTS["last_checkpoint"]
    checkpoint_count: int = _DEFAULTS["checkpoint_count"]

    # Context Search
    context_search_enabled: bool = _DEFAULTS["context_search_enabled"]
    context_flashback_sim: float = _DEFAULTS["context_flashback_sim"]
    context_flashback_arousal: float = _DEFAULTS["context_flashback_arousal"]
    context_cache_max_size: int = _DEFAULTS["context_cache_max_size"]
    context_cache_sim_threshold: float = _DEFAULTS["context_cache_sim_threshold"]

    # Skills
    skills_auto_improve: str = "auto"  # "auto" | "ask" | "off"

    # Metrics
    total_sessions: int = _DEFAULTS["total_sessions"]

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

    @property
    def contexts_path(self) -> Path:
        p = Path(self.contexts_dir)
        if p.is_absolute():
            return p
        return Path(self._base_dir) / self.contexts_dir

    @property
    def identity_soul_path(self) -> Path:
        p = Path(self.identity_soul)
        if p.is_absolute():
            return p
        return Path(self._base_dir) / self.identity_soul

    @property
    def identity_user_path(self) -> Path:
        p = Path(self.identity_user)
        if p.is_absolute():
            return p
        return Path(self._base_dir) / self.identity_user

    @property
    def knowledge_summary_path(self) -> Path:
        p = Path(self.knowledge_summary)
        if p.is_absolute():
            return p
        return Path(self._base_dir) / self.knowledge_summary

    @property
    def knowledge_error_patterns_path(self) -> Path:
        p = Path(self.knowledge_error_patterns)
        if p.is_absolute():
            return p
        return Path(self._base_dir) / self.knowledge_error_patterns

    @staticmethod
    def _resolve_identity_soul(identity: dict) -> str:
        """Resolve soul path with backward compat for 'agent' key."""
        if "soul" in identity:
            return identity["soul"]
        if "agent" in identity:
            print(
                "WARNING: [cogmem.identity] agent= is deprecated. "
                "Rename to soul= and run 'cogmem migrate'. "
                "See https://pypi.org/project/cogmem-agent/",
                file=sys.stderr,
            )
            return identity["agent"]
        return _DEFAULTS["identity_soul"]

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
        identity = section.get("identity", {})
        knowledge = section.get("knowledge", {})
        session = section.get("session", {})
        crystallization = section.get("crystallization", {})
        context_search = section.get("context_search", {})
        metrics = section.get("metrics", {})
        skills = section.get("skills", {})

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
            identity_soul=cls._resolve_identity_soul(identity),
            identity_user=identity.get("user", _DEFAULTS["identity_user"]),
            knowledge_summary=knowledge.get(
                "summary", _DEFAULTS["knowledge_summary"]
            ),
            knowledge_error_patterns=knowledge.get(
                "error_patterns", _DEFAULTS["knowledge_error_patterns"]
            ),
            contexts_dir=session.get("contexts_dir", _DEFAULTS["contexts_dir"]),
            recent_logs=session.get("recent_logs", _DEFAULTS["recent_logs"]),
            prefer_compact=session.get("prefer_compact", _DEFAULTS["prefer_compact"]),
            token_budget=session.get("token_budget", _DEFAULTS["token_budget"]),
            pattern_threshold=crystallization.get(
                "pattern_threshold", _DEFAULTS["pattern_threshold"]
            ),
            error_threshold=crystallization.get(
                "error_threshold", _DEFAULTS["error_threshold"]
            ),
            log_days_threshold=crystallization.get(
                "log_days_threshold", _DEFAULTS["log_days_threshold"]
            ),
            checkpoint_interval_days=crystallization.get(
                "checkpoint_interval_days", _DEFAULTS["checkpoint_interval_days"]
            ),
            last_checkpoint=crystallization.get(
                "last_checkpoint", _DEFAULTS["last_checkpoint"]
            ),
            checkpoint_count=crystallization.get(
                "checkpoint_count", _DEFAULTS["checkpoint_count"]
            ),
            context_search_enabled=context_search.get(
                "enabled", _DEFAULTS["context_search_enabled"]
            ),
            context_flashback_sim=context_search.get(
                "flashback_sim", _DEFAULTS["context_flashback_sim"]
            ),
            context_flashback_arousal=context_search.get(
                "flashback_arousal", _DEFAULTS["context_flashback_arousal"]
            ),
            context_cache_max_size=context_search.get(
                "cache_max_size", _DEFAULTS["context_cache_max_size"]
            ),
            context_cache_sim_threshold=context_search.get(
                "cache_sim_threshold", _DEFAULTS["context_cache_sim_threshold"]
            ),
            total_sessions=metrics.get(
                "total_sessions", _DEFAULTS["total_sessions"]
            ),
            skills_auto_improve=str(skills.get("auto_improve", "auto")),
            _base_dir=str(p.parent),
        )

    @classmethod
    def find_and_load(cls, start_dir: Optional[str | Path] = None) -> CogMemConfig:
        """Search for cogmem.toml from start_dir upward. Falls back to env var or defaults."""
        env_path = os.environ.get("COGMEM_CONFIG")
        if env_path:
            return cls.from_toml(env_path)

        d = Path(start_dir) if start_dir else Path.cwd()
        for _ in range(64):  # depth limit to avoid hangs on network mounts
            candidate = d / "cogmem.toml"
            if candidate.exists():
                return cls.from_toml(candidate)
            parent = d.parent
            if parent == d:
                break
            d = parent

        return cls()
