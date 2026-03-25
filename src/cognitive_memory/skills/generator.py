"""Skill generation and improvement logic."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from .types import (
    Skill, SkillCategory, SkillCreationRequest, SuccessMetric,
    UsageStats, SKILL_CATEGORIES, PerformanceMetric
)


class SkillGenerator:
    """Generates new skills and improves existing ones."""

    def __init__(self):
        pass

    def create_new_skill(self, request: SkillCreationRequest) -> Skill:
        """Create a new skill based on the creation request."""
        skill_id = self._generate_skill_id()
        category = self._determine_skill_category(request.context)
        name = self._generate_skill_name(request.context)
        execution_pattern = self._generate_execution_pattern(request)
        success_metrics = self._generate_success_metrics(request)

        skill = Skill(
            id=skill_id,
            name=name,
            category=category,
            description=request.context,
            execution_pattern=execution_pattern,
            success_metrics=success_metrics,
            improvement_history=[],
            usage_stats=UsageStats(
                total_executions=0,
                successful_executions=0,
                average_effectiveness=request.performance.effectiveness,
                last_used_at=None,
                frequency=0.0
            ),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            version=1
        )

        return skill

    def improve_existing_skill(
        self,
        skill: Skill,
        performance: PerformanceMetric,
        user_feedback: str
    ) -> Skill | None:
        """Improve an existing skill based on performance feedback."""
        from .types import ImprovementRecord

        LOW_PERFORMANCE_THRESHOLD = 0.7
        is_low_performance = performance.effectiveness < LOW_PERFORMANCE_THRESHOLD

        improvement_gain = performance.effectiveness - skill.usage_stats.average_effectiveness

        if not is_low_performance and improvement_gain < 0.05:
            return None

        if is_low_performance and improvement_gain >= 0:
            improvement_gain = max(improvement_gain, LOW_PERFORMANCE_THRESHOLD - performance.effectiveness)

        improvement = ImprovementRecord(
            timestamp=datetime.now().isoformat(),
            description=f"Performance adjustment based on feedback: {user_feedback}",
            before_value=skill.usage_stats.average_effectiveness,
            after_value=performance.effectiveness,
            effectiveness_gain=abs(improvement_gain)
        )

        # Update skill
        skill.improvement_history.append(improvement)
        skill.updated_at = datetime.now().isoformat()
        skill.version += 1

        # Improve execution pattern if performance is low
        if performance.effectiveness < 0.5:
            skill.execution_pattern = self._improve_execution_pattern(
                skill.execution_pattern,
                user_feedback,
                performance
            )

        return skill

    def _generate_skill_id(self) -> str:
        """Generate unique skill ID."""
        timestamp = int(datetime.now().timestamp())
        unique_part = str(uuid.uuid4())[:8]
        return f"skill_{timestamp}_{unique_part}"

    def _determine_skill_category(self, context: str) -> SkillCategory:
        """Determine the most appropriate category for the skill."""
        context_lower = context.lower()

        # Category classification rules
        if any(word in context_lower for word in ['conversation', 'chat', 'talk', 'discuss', 'respond']):
            return 'conversation-skills'

        if any(word in context_lower for word in ['proactive', 'suggest', 'recommend', 'remind', 'alert']):
            return 'proactive-skills'

        if any(word in context_lower for word in ['automate', 'schedule', 'routine', 'automatic', 'cron']):
            return 'automation-skills'

        if any(word in context_lower for word in ['learn', 'improve', 'study', 'analyze', 'understand']):
            return 'learning-skills'

        # Default to meta-skills for complex or multi-category contexts
        return 'meta-skills'

    def _generate_skill_name(self, context: str) -> str:
        """Generate a descriptive name for the skill."""
        # Extract key words and create title
        words = context.split()[:4]  # Take first 4 words

        # Clean and capitalize words
        clean_words = []
        for word in words:
            clean_word = ''.join(c for c in word if c.isalnum())
            if clean_word and len(clean_word) > 2:
                clean_words.append(clean_word.capitalize())

        if not clean_words:
            return "Generated Skill"

        return ' '.join(clean_words) + " Skill"

    def _generate_execution_pattern(self, request: SkillCreationRequest) -> str:
        """Generate minimal stub pattern. Use skill-creator for quality content."""
        context = request.context
        feedback = request.user_feedback

        lines = [f"# {context}"]
        if feedback:
            lines.append(f"\n{feedback}")
        lines.append("\n<!-- Use /skill-creator to develop full execution steps -->")
        return "\n".join(lines)

    def _generate_success_metrics(self, request: SkillCreationRequest) -> List[SuccessMetric]:
        """Generate success metrics for the new skill."""
        metrics = [
            SuccessMetric(
                name="Effectiveness",
                description="Overall success rate of skill execution",
                measurement_method="User feedback and performance metrics",
                target_value=0.8,
                current_value=request.performance.effectiveness
            ),
            SuccessMetric(
                name="User Satisfaction",
                description="User satisfaction score based on reactions and feedback",
                measurement_method="User reactions, feedback, and ratings",
                target_value=0.8,
                current_value=request.performance.user_satisfaction
            ),
            SuccessMetric(
                name="Execution Speed",
                description="Time to complete the task successfully",
                measurement_method="Automated timing and performance monitoring",
                target_value=request.performance.execution_time * 0.8,  # Target 20% improvement
                current_value=request.performance.execution_time
            ),
            SuccessMetric(
                name="Error Rate",
                description="Frequency of errors during skill execution",
                measurement_method="Error detection and logging",
                target_value=0.1,  # Target < 10% error rate
                current_value=request.performance.error_rate
            )
        ]

        return metrics

    def _improve_execution_pattern(
        self,
        current_pattern: str,
        user_feedback: str,
        performance: PerformanceMetric
    ) -> str:
        """Append improvement note. Use skill-creator for substantive improvements."""
        note = (
            f"\n\n## Improvement Note ({datetime.now().strftime('%Y-%m-%d')})\n"
            f"- Effectiveness: {performance.effectiveness:.2f}\n"
            f"- Feedback: {user_feedback}\n"
            f"<!-- Run /skill-creator to apply improvements -->"
        )
        return current_pattern + note