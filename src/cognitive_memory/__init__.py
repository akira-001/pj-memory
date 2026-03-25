"""Cognitive Memory — human-like cognitive memory for AI agents."""

from __future__ import annotations

from ._version import __version__
from .config import CogMemConfig
from .context import SearchCache, filter_flashbacks
from .store import MemoryStore
from .types import MemoryEntry, SearchResponse, SearchResult

# Skills Memory Layer
from .skills import (
    Skill, SkillCategory, SkillsManager, SkillsStore,
    PerformanceMetric, LearningLoopResult, SKILL_CATEGORIES
)


def search(query: str, top_k: int = 5, config: CogMemConfig | None = None) -> SearchResponse:
    """Convenience function: auto-find cogmem.toml and search."""
    if config is None:
        config = CogMemConfig.find_and_load()
    with MemoryStore(config) as store:
        return store.search(query, top_k)


def search_skills(query: str, config: CogMemConfig | None = None, top_k: int = 5) -> list[Skill]:
    """Convenience function: search for skills using auto-found config."""
    if config is None:
        config = CogMemConfig.find_and_load()
    skills_manager = SkillsManager(config)
    return skills_manager.search_skills(query, top_k=top_k)


__all__ = [
    "__version__",
    "CogMemConfig",
    "MemoryEntry",
    "MemoryStore",
    "SearchCache",
    "SearchResponse",
    "SearchResult",
    "filter_flashbacks",
    "search",
    # Skills Memory Layer
    "Skill",
    "SkillCategory",
    "SkillsManager",
    "SkillsStore",
    "PerformanceMetric",
    "LearningLoopResult",
    "SKILL_CATEGORIES",
    "search_skills",
]
