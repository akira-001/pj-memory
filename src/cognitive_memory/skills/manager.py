"""Main Skills Manager integrating all skills functionality."""

from __future__ import annotations

from typing import Dict, List, Optional

from ..config import CogMemConfig
from .types import Skill, SkillCategory, PerformanceMetric, LearningLoopResult
from .store import SkillsStore
from .evaluator import SkillEvaluator
from .generator import SkillGenerator
from .reflection import SkillReflectionLoop


class SkillsManager:
    """
    Main manager for the Skills Memory Layer in cognitive memory.

    Provides a unified interface for:
    - Skill storage and retrieval
    - Read-Write reflective learning loop
    - Performance evaluation and improvement
    - Skill generation and optimization
    """

    def __init__(self, config: CogMemConfig):
        self.config = config
        self.store = SkillsStore(config)
        self.evaluator = SkillEvaluator()
        self.generator = SkillGenerator()
        self.reflection_loop = SkillReflectionLoop(self.store)

    # --- Core Skill Management ---

    def save_skill(self, skill: Skill) -> None:
        """Save a skill to storage."""
        self.store.save_skill(skill)

    def load_skill(self, category: SkillCategory, skill_id: str) -> Optional[Skill]:
        """Load a specific skill."""
        return self.store.load_skill(category, skill_id)

    def load_all_skills(self) -> Dict[SkillCategory, List[Skill]]:
        """Load all skills grouped by category."""
        return self.store.load_all_skills()

    def search_skills(
        self,
        query: str,
        category: Optional[SkillCategory] = None,
        top_k: int = 5,
        min_effectiveness: float = 0.0
    ) -> List[Skill]:
        """Search for skills matching query."""
        return self.store.search_skills(query, category, top_k, min_effectiveness)

    def delete_skill(self, skill_id: str) -> bool:
        """Delete a skill."""
        return self.store.delete_skill(skill_id)

    # --- Read-Write Reflective Learning Loop ---

    def read_phase(self, context: str) -> Dict[str, any]:
        """
        Read Phase: Analyze context and find applicable skills.

        Args:
            context: Current situation description

        Returns:
            Dict with applicable skills and analysis
        """
        return self.reflection_loop.read_phase(context)

    def select_best_skill(self, applicable_skills: List[Skill], context: str) -> Optional[Skill]:
        """Select the best skill for execution."""
        return self.reflection_loop.select_best_skill(applicable_skills, context)

    async def write_phase(
        self,
        executed_skill: Optional[Skill],
        context: str,
        performance: PerformanceMetric,
        user_feedback: str
    ) -> LearningLoopResult:
        """
        Write Phase: Evaluate results and create/improve skills.

        Args:
            executed_skill: The skill that was executed
            context: Execution context
            performance: Performance metrics
            user_feedback: User feedback

        Returns:
            LearningLoopResult indicating what action was taken
        """
        return await self.reflection_loop.write_phase(
            executed_skill, context, performance, user_feedback
        )

    def reflect_phase(
        self,
        learning_result: LearningLoopResult,
        context: str,
        performance: PerformanceMetric
    ) -> Dict[str, any]:
        """Reflect on learning outcomes and extract insights."""
        return self.reflection_loop.reflect_phase(learning_result, context, performance)

    # --- Complete Learning Loop ---

    async def execute_learning_loop(
        self,
        context: str,
        performance: PerformanceMetric,
        user_feedback: str
    ) -> Dict[str, any]:
        """
        Execute complete Read-Write learning loop.

        Args:
            context: Situation context
            performance: Performance metrics
            user_feedback: User feedback

        Returns:
            Complete learning loop results
        """
        # Read Phase
        read_result = self.read_phase(context)
        applicable_skills = read_result["applicable_skills"]
        selected_skill = self.select_best_skill(applicable_skills, context)

        # Write Phase
        write_result = await self.write_phase(
            executed_skill=selected_skill,
            context=context,
            performance=performance,
            user_feedback=user_feedback
        )

        # Reflect Phase
        reflection = self.reflect_phase(write_result, context, performance)

        return {
            "read_phase": read_result,
            "selected_skill": selected_skill.id if selected_skill else None,
            "write_phase": write_result,
            "reflection": reflection,
            "learning_summary": self._generate_learning_summary(
                read_result, selected_skill, write_result, reflection
            )
        }

    # --- Skill Analytics and Management ---

    def get_skill_stats(self) -> Dict[str, any]:
        """Get comprehensive skill statistics."""
        all_skills = self.store.load_all_skills()
        total_skills = sum(len(skills) for skills in all_skills.values())

        category_counts = {cat: len(skills) for cat, skills in all_skills.items()}

        # Calculate averages
        all_skills_flat = [skill for skills in all_skills.values() for skill in skills]

        if all_skills_flat:
            avg_effectiveness = sum(s.usage_stats.average_effectiveness for s in all_skills_flat) / len(all_skills_flat)
            total_executions = sum(s.usage_stats.total_executions for s in all_skills_flat)
            total_successful = sum(s.usage_stats.successful_executions for s in all_skills_flat)
            overall_success_rate = total_successful / total_executions if total_executions > 0 else 0.0
        else:
            avg_effectiveness = 0.0
            total_executions = 0
            total_successful = 0
            overall_success_rate = 0.0

        return {
            "total_skills": total_skills,
            "category_counts": category_counts,
            "average_effectiveness": avg_effectiveness,
            "total_executions": total_executions,
            "overall_success_rate": overall_success_rate,
            "most_effective_skills": self.get_top_skills(limit=5)
        }

    def get_top_skills(self, limit: int = 10) -> List[Skill]:
        """Get top performing skills."""
        return self.store.get_top_skills(limit)

    def get_skills_by_category(self, category: SkillCategory) -> List[Skill]:
        """Get all skills in a category."""
        return self.store.get_skills_by_category(category)

    def evaluate_skill(self, skill: Skill, recent_window_days: int = 30) -> Dict[str, any]:
        """Get comprehensive evaluation of a skill."""
        return self.evaluator.evaluate_skill_effectiveness(skill, recent_window_days)

    def create_skill_from_context(
        self,
        context: str,
        performance: PerformanceMetric,
        user_feedback: str = ""
    ) -> Skill:
        """Create a new skill directly from context and performance."""
        existing_skills = [skill for skills in self.load_all_skills().values() for skill in skills]

        from .types import SkillCreationRequest
        request = SkillCreationRequest(
            context=context,
            existing_skills=existing_skills,
            user_feedback=user_feedback,
            performance=performance
        )

        new_skill = self.generator.create_new_skill(request)
        self.save_skill(new_skill)
        return new_skill

    # --- Utility Methods ---

    def find_similar_skills(self, context: str, threshold: float = 0.6) -> List[Skill]:
        """Find skills similar to the given context."""
        all_skills = [skill for skills in self.load_all_skills().values() for skill in skills]
        return self.evaluator.find_similar_skills(context, all_skills, threshold)

    def _generate_learning_summary(
        self,
        read_result: Dict[str, any],
        selected_skill: Optional[Skill],
        write_result: LearningLoopResult,
        reflection: Dict[str, any]
    ) -> Dict[str, any]:
        """Generate a summary of the learning loop execution."""
        return {
            "skills_analyzed": len(read_result["applicable_skills"]),
            "skill_selected": selected_skill.name if selected_skill else "None",
            "learning_action": write_result.action,
            "performance_level": reflection["performance_level"],
            "learning_opportunity": reflection["learning_opportunity"],
            "key_insights": reflection["strategic_insights"][:3]  # Top 3 insights
        }

    # --- Integration with Cognitive Memory ---

    def integrate_with_memory_search(self, query: str, memory_results: List[any]) -> List[Skill]:
        """
        Integrate skills with cognitive memory search results.

        Args:
            query: Search query
            memory_results: Results from cognitive memory search

        Returns:
            List of skills that could enhance or learn from the memory results
        """
        # Extract contexts from memory results
        contexts = []
        for result in memory_results:
            if hasattr(result, 'content'):
                contexts.append(result.content)

        # Find skills applicable to these contexts
        relevant_skills = []
        for context in contexts:
            skills = self.search_skills(context, top_k=3)
            relevant_skills.extend(skills)

        # Remove duplicates and sort by effectiveness
        unique_skills = list({skill.id: skill for skill in relevant_skills}.values())
        return sorted(unique_skills, key=lambda s: s.usage_stats.average_effectiveness, reverse=True)

    def suggest_skill_for_memory_context(self, memory_context: str) -> Optional[Skill]:
        """Suggest the best skill for a given memory context."""
        applicable_skills = self.search_skills(memory_context, top_k=5)
        return self.select_best_skill(applicable_skills, memory_context)