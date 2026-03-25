"""Types and interfaces for Skills Memory Layer."""

from __future__ import annotations

from typing import List, Literal, Optional, Union
from dataclasses import dataclass
from datetime import datetime


# Skill categories (matching SlackBot implementation)
SKILL_CATEGORIES = [
    "conversation-skills",
    "proactive-skills",
    "automation-skills",
    "learning-skills",
    "meta-skills"
]

SkillCategory = Literal[
    "conversation-skills",
    "proactive-skills",
    "automation-skills",
    "learning-skills",
    "meta-skills"
]


@dataclass
class SuccessMetric:
    """Metric for measuring skill effectiveness."""
    name: str
    description: str
    measurement_method: str
    target_value: Optional[float] = None
    current_value: Optional[float] = None


@dataclass
class ImprovementRecord:
    """Record of skill improvement over time."""
    timestamp: str
    description: str
    before_value: Optional[float] = None
    after_value: Optional[float] = None
    effectiveness_gain: float = 0.0  # 0.0-1.0


@dataclass
class UsageStats:
    """Statistics tracking skill usage and performance."""
    total_executions: int = 0
    successful_executions: int = 0
    average_effectiveness: float = 0.5
    last_used_at: Optional[str] = None
    frequency: float = 0.0  # executions per day


@dataclass
class Skill:
    """Core skill representation."""
    id: str
    name: str
    category: SkillCategory
    description: str
    execution_pattern: str
    success_metrics: List[SuccessMetric]
    improvement_history: List[ImprovementRecord]
    usage_stats: UsageStats
    created_at: str
    updated_at: str
    version: int = 1


@dataclass
class PerformanceMetric:
    """Performance measurement for skill execution."""
    effectiveness: float  # 0.0-1.0
    user_satisfaction: float  # 0.0-1.0
    execution_time: float  # milliseconds
    error_rate: float  # 0.0-1.0


@dataclass
class SkillCreationRequest:
    """Request to create a new skill."""
    context: str
    existing_skills: List[Skill]
    user_feedback: str
    performance: PerformanceMetric


@dataclass
class LearningLoopResult:
    """Result of Read-Write learning loop execution."""
    action: Literal["create", "update", "none"]
    skill: Optional[Skill] = None
    improvement_details: Optional[str] = None
    next_steps: List[str] = None

    def __post_init__(self):
        if self.next_steps is None:
            self.next_steps = []


# Constants for skill creation and improvement thresholds
SKILL_CREATION_THRESHOLD = 0.3  # Create new skill if improvement potential > 30%
MIN_FREQUENCY_FOR_NEW_SKILL = 0.1  # Minimum weekly frequency for new skill consideration
EFFECTIVENESS_IMPROVEMENT_THRESHOLD = 0.15  # 15% improvement required for skill creation