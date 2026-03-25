"""Read-Write Reflective Learning Loop for skill evolution."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .types import Skill, PerformanceMetric, LearningLoopResult, SkillCreationRequest
from .store import SkillsStore
from .evaluator import SkillEvaluator
from .generator import SkillGenerator


class SkillReflectionLoop:
    """
    Implements the Read-Write Reflective Learning Loop from Memento-Skills.

    The loop consists of:
    1. Read Phase: Analyze context and identify applicable skills
    2. Execute Phase: Apply selected skill and monitor performance
    3. Write Phase: Evaluate results and create/improve skills
    4. Reflect Phase: Learn from outcomes and update knowledge
    """

    def __init__(self, store: SkillsStore):
        self.store = store
        self.evaluator = SkillEvaluator()
        self.generator = SkillGenerator()

    def read_phase(self, context: str) -> Dict[str, any]:
        """
        Read Phase: Analyze current context and identify applicable skills.

        Args:
            context: Current situation description

        Returns:
            Dict containing applicable skills and analysis
        """
        # Search for applicable skills
        applicable_skills = self.store.search_skills(context, top_k=10)

        # Rank skills by applicability and effectiveness
        ranked_skills = self._rank_skills_by_context(applicable_skills, context)

        # Analysis of the situation
        analysis = {
            "context": context,
            "total_applicable_skills": len(applicable_skills),
            "top_skills": ranked_skills[:3],  # Top 3 most applicable
            "skill_categories_represented": list(set(s.category for s in applicable_skills)),
            "best_skill_effectiveness": ranked_skills[0].usage_stats.average_effectiveness if ranked_skills else 0.0
        }

        return {
            "applicable_skills": ranked_skills,
            "analysis": analysis
        }

    def select_best_skill(self, applicable_skills: List[Skill], context: str) -> Optional[Skill]:
        """
        Select the best skill for execution based on context and performance.

        Args:
            applicable_skills: List of skills that could apply
            context: Current situation context

        Returns:
            Best skill to execute, or None if no suitable skill
        """
        if not applicable_skills:
            return None

        # Score skills based on multiple factors
        scored_skills = []
        for skill in applicable_skills:
            score = self._calculate_skill_selection_score(skill, context)
            scored_skills.append((skill, score))

        # Sort by score and return best
        scored_skills.sort(key=lambda x: x[1], reverse=True)
        return scored_skills[0][0] if scored_skills else None

    async def write_phase(
        self,
        executed_skill: Optional[Skill],
        context: str,
        performance: PerformanceMetric,
        user_feedback: str
    ) -> LearningLoopResult:
        """
        Write Phase: Evaluate execution results and determine learning actions.

        Args:
            executed_skill: The skill that was executed (if any)
            context: Execution context
            performance: Performance metrics from execution
            user_feedback: User feedback on the result

        Returns:
            LearningLoopResult indicating what learning action to take
        """
        # Update executed skill's performance
        if executed_skill:
            await self._update_skill_performance(executed_skill, performance)

        # Evaluate whether to create new skill
        existing_skills = list(self.store.load_all_skills().values())
        flat_skills = [skill for skills_list in existing_skills for skill in skills_list]

        should_create = self.evaluator.should_create_new_skill(
            context=context,
            performance=performance,
            user_feedback=user_feedback,
            executed_skill=executed_skill,
            existing_skills=flat_skills
        )

        if should_create["create"]:
            # Create new skill
            request = SkillCreationRequest(
                context=context,
                existing_skills=flat_skills,
                user_feedback=user_feedback,
                performance=performance
            )
            new_skill = self.generator.create_new_skill(request)

            self.store.save_skill(new_skill)

            return LearningLoopResult(
                action="create",
                skill=new_skill,
                improvement_details=should_create["reason"],
                next_steps=[
                    "Test new skill in similar contexts",
                    "Monitor effectiveness over time",
                    "Gather more user feedback",
                    "Refine execution pattern based on results"
                ]
            )

        # Check if existing skill needs improvement
        if executed_skill and performance.effectiveness < 0.7:
            improved_skill = self.generator.improve_existing_skill(
                executed_skill, performance, user_feedback
            )

            if improved_skill:
                self.store.save_skill(improved_skill)

                return LearningLoopResult(
                    action="update",
                    skill=improved_skill,
                    improvement_details="Skill updated based on performance feedback",
                    next_steps=[
                        "Re-test improved skill",
                        "Validate effectiveness improvements",
                        "Monitor for regression"
                    ]
                )

        # No significant learning action needed
        return LearningLoopResult(
            action="none",
            improvement_details=f"Performance acceptable ({performance.effectiveness:.2f}). No action needed.",
            next_steps=["Continue monitoring performance"]
        )

    def reflect_phase(
        self,
        learning_result: LearningLoopResult,
        context: str,
        performance: PerformanceMetric
    ) -> Dict[str, any]:
        """
        Reflect Phase: Analyze learning outcomes and update strategic knowledge.

        Args:
            learning_result: Result from write phase
            context: Original context
            performance: Performance metrics

        Returns:
            Dict containing reflection insights
        """
        reflection = {
            "learning_action_taken": learning_result.action,
            "context_complexity": self._assess_context_complexity(context),
            "performance_level": self._categorize_performance(performance),
            "learning_opportunity": self._assess_learning_opportunity(learning_result),
            "strategic_insights": self._extract_strategic_insights(context, performance, learning_result)
        }

        return reflection

    def _rank_skills_by_context(self, skills: List[Skill], context: str) -> List[Skill]:
        """Rank skills by their applicability to the current context."""
        scored_skills = []

        for skill in skills:
            # Calculate context similarity
            context_score = self.evaluator.calculate_context_similarity(context, skill.description)

            # Factor in skill effectiveness
            effectiveness_score = skill.usage_stats.average_effectiveness

            # Consider recency (more recent = better)
            recency_score = self._calculate_recency_score(skill)

            # Combined score
            total_score = (
                context_score * 0.4 +
                effectiveness_score * 0.4 +
                recency_score * 0.2
            )

            scored_skills.append((skill, total_score))

        # Sort by score and return skills only
        scored_skills.sort(key=lambda x: x[1], reverse=True)
        return [skill for skill, score in scored_skills]

    def _calculate_skill_selection_score(self, skill: Skill, context: str) -> float:
        """Calculate comprehensive score for skill selection."""
        # Base effectiveness
        effectiveness = skill.usage_stats.average_effectiveness

        # Context relevance
        context_relevance = self.evaluator.calculate_context_similarity(context, skill.description)

        # Success rate
        success_rate = (
            skill.usage_stats.successful_executions / skill.usage_stats.total_executions
            if skill.usage_stats.total_executions > 0 else 0.0
        )

        # Recency factor (prefer recently used skills)
        recency = self._calculate_recency_score(skill)

        # Combine scores with weights
        score = (
            effectiveness * 0.35 +
            context_relevance * 0.30 +
            success_rate * 0.25 +
            recency * 0.10
        )

        return score

    def _calculate_recency_score(self, skill: Skill) -> float:
        """Calculate recency score (0-1) based on last usage."""
        if not skill.usage_stats.last_used_at:
            return 0.1  # Small score for never-used skills

        from datetime import datetime, timedelta

        try:
            last_used = datetime.fromisoformat(skill.usage_stats.last_used_at.replace('Z', '+00:00'))
            days_ago = (datetime.now() - last_used).days

            # Decay function: full score for < 1 day, 0.5 for 7 days, 0.1 for 30 days
            if days_ago <= 1:
                return 1.0
            elif days_ago <= 7:
                return 0.5
            elif days_ago <= 30:
                return 0.2
            else:
                return 0.1

        except ValueError:
            return 0.1

    async def _update_skill_performance(self, skill: Skill, performance: PerformanceMetric) -> None:
        """Update skill performance statistics."""
        skill.usage_stats.total_executions += 1

        if performance.effectiveness > 0.6:
            skill.usage_stats.successful_executions += 1

        # Update moving average of effectiveness
        alpha = 0.2  # Learning rate
        skill.usage_stats.average_effectiveness = (
            alpha * performance.effectiveness +
            (1 - alpha) * skill.usage_stats.average_effectiveness
        )

        # Update last used timestamp
        from datetime import datetime
        skill.usage_stats.last_used_at = datetime.now().isoformat()

        # Save updated skill
        self.store.save_skill(skill)

    def _assess_context_complexity(self, context: str) -> str:
        """Assess the complexity of the given context."""
        word_count = len(context.split())
        unique_concepts = len(set(context.lower().split()))

        if word_count < 10 and unique_concepts < 8:
            return "simple"
        elif word_count < 25 and unique_concepts < 15:
            return "moderate"
        else:
            return "complex"

    def _categorize_performance(self, performance: PerformanceMetric) -> str:
        """Categorize performance level."""
        if performance.effectiveness >= 0.8:
            return "excellent"
        elif performance.effectiveness >= 0.6:
            return "good"
        elif performance.effectiveness >= 0.4:
            return "fair"
        else:
            return "poor"

    def _assess_learning_opportunity(self, learning_result: LearningLoopResult) -> str:
        """Assess the type of learning opportunity."""
        if learning_result.action == "create":
            return "new_skill_creation"
        elif learning_result.action == "update":
            return "skill_improvement"
        else:
            return "performance_monitoring"

    def _extract_strategic_insights(
        self,
        context: str,
        performance: PerformanceMetric,
        learning_result: LearningLoopResult
    ) -> List[str]:
        """Extract strategic insights from the learning episode."""
        insights = []

        if learning_result.action == "create":
            insights.append(f"Identified new skill category needed for contexts like: {context[:50]}...")

        if performance.effectiveness < 0.4:
            insights.append("Consider enhancing fundamental capabilities in this area")

        if performance.error_rate > 0.5:
            insights.append("Error handling and validation need improvement")

        if performance.execution_time > 5000:
            insights.append("Performance optimization opportunities identified")

        if not insights:
            insights.append("Steady performance - continue current approach")

        return insights