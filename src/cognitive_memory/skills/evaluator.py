"""Skill evaluation and performance assessment."""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timedelta

from .types import Skill, PerformanceMetric, SKILL_CREATION_THRESHOLD


class SkillEvaluator:
    """Evaluates skill performance and determines improvement opportunities."""

    def __init__(self, embedder=None):
        self._embedder = embedder

    def should_create_new_skill(
        self,
        context: str,
        performance: PerformanceMetric,
        user_feedback: str,
        executed_skill: Optional[Skill] = None,
        existing_skills: Optional[List[Skill]] = None
    ) -> dict:
        """
        Determine if a new skill should be created based on performance and context.

        Returns:
            dict: {
                "create": bool,
                "reason": str,
                "confidence": float,
                "existing_skills": List[Skill]
            }
        """
        existing_skills = existing_skills or []

        # Don't create if existing skill is already highly effective
        if executed_skill and performance.effectiveness > 0.8:
            return {
                "create": False,
                "reason": f"Existing skill '{executed_skill.name}' already effective ({performance.effectiveness:.2f})",
                "confidence": 0.9,
                "existing_skills": []
            }

        # Calculate improvement potential
        improvement_potential = 1.0 - performance.effectiveness
        if improvement_potential < SKILL_CREATION_THRESHOLD:
            return {
                "create": False,
                "reason": f"Low improvement potential ({improvement_potential:.2f} < {SKILL_CREATION_THRESHOLD})",
                "confidence": 0.8,
                "existing_skills": []
            }

        # Check for similar existing skills
        similar_skills = self.find_similar_skills(context, existing_skills)
        if similar_skills and len(similar_skills) > 0:
            # If similar skills exist but perform poorly, consider creating new one
            best_similar = max(similar_skills, key=lambda s: s.usage_stats.average_effectiveness)
            if best_similar.usage_stats.average_effectiveness > 0.6:
                return {
                    "create": False,
                    "reason": f"Similar skill '{best_similar.name}' already exists with good performance",
                    "confidence": 0.7,
                    "existing_skills": similar_skills
                }

        # Assess user feedback sentiment
        feedback_score = self.assess_user_feedback(user_feedback)

        # Calculate creation confidence
        confidence = self._calculate_creation_confidence(
            improvement_potential,
            feedback_score,
            performance,
            len(similar_skills)
        )

        if confidence > 0.6:
            return {
                "create": True,
                "reason": f"High improvement potential ({improvement_potential:.2f}) with positive feedback",
                "confidence": confidence,
                "existing_skills": similar_skills
            }
        else:
            return {
                "create": False,
                "reason": f"Low confidence ({confidence:.2f}) for new skill creation",
                "confidence": confidence,
                "existing_skills": similar_skills
            }

    def find_similar_skills(self, context: str, skills: List[Skill], threshold: float = 0.6) -> List[Skill]:
        """Find skills similar to the given context."""
        similar_skills = []
        context_lower = context.lower()
        context_words = set(context_lower.split())

        for skill in skills:
            similarity = self.calculate_context_similarity(context, skill.description)
            if similarity >= threshold:
                similar_skills.append(skill)

        return sorted(similar_skills, key=lambda s: s.usage_stats.average_effectiveness, reverse=True)

    def calculate_context_similarity(self, context1: str, context2: str) -> float:
        """Calculate similarity using vector embeddings (primary) or word overlap (fallback)."""
        if self._embedder:
            try:
                vecs = self._embedder.embed_batch([context1, context2])
                if vecs and len(vecs) == 2:
                    from ..scoring import cosine_sim, normalize
                    v1 = normalize(vecs[0])
                    v2 = normalize(vecs[1])
                    return max(0.0, cosine_sim(v1, v2))
            except Exception:
                pass

        # Fallback: word overlap (Jaccard)
        words1 = set(context1.lower().split())
        words2 = set(context2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def assess_user_feedback(self, feedback: str) -> float:
        """
        Assess user feedback sentiment.

        Returns:
            float: Score from -1.0 (very negative) to 1.0 (very positive)
        """
        feedback_lower = feedback.lower()

        # Positive indicators
        positive_words = [
            'good', 'great', 'excellent', 'helpful', 'useful', 'perfect',
            'love', 'like', 'amazing', 'wonderful', 'fantastic', '+1',
            'thumbsup', 'heart', '👍', '❤️', '🎉'
        ]

        # Negative indicators
        negative_words = [
            'bad', 'terrible', 'awful', 'useless', 'wrong', 'error',
            'hate', 'dislike', 'horrible', 'disappointing', '-1',
            'thumbsdown', '👎', '❌', '😞'
        ]

        positive_score = sum(1 for word in positive_words if word in feedback_lower)
        negative_score = sum(1 for word in negative_words if word in feedback_lower)

        if positive_score + negative_score == 0:
            return 0.0  # Neutral

        return (positive_score - negative_score) / (positive_score + negative_score)

    def evaluate_skill_effectiveness(self, skill: Skill, recent_window_days: int = 30) -> dict:
        """
        Evaluate overall skill effectiveness.

        Returns:
            dict: Comprehensive evaluation metrics
        """
        now = datetime.now()
        recent_threshold = now - timedelta(days=recent_window_days)

        # Calculate success rate
        success_rate = (
            skill.usage_stats.successful_executions / skill.usage_stats.total_executions
            if skill.usage_stats.total_executions > 0 else 0.0
        )

        # Assess improvement trend
        improvement_trend = self._assess_improvement_trend(skill)

        # Calculate recency factor
        recency_factor = self._calculate_recency_factor(skill, recent_threshold)

        # Overall effectiveness score
        overall_score = (
            skill.usage_stats.average_effectiveness * 0.4 +
            success_rate * 0.3 +
            improvement_trend * 0.2 +
            recency_factor * 0.1
        )

        return {
            "overall_score": overall_score,
            "average_effectiveness": skill.usage_stats.average_effectiveness,
            "success_rate": success_rate,
            "improvement_trend": improvement_trend,
            "recency_factor": recency_factor,
            "total_executions": skill.usage_stats.total_executions,
            "days_since_last_use": self._days_since_last_use(skill),
            "recommendation": self._generate_recommendation(overall_score, skill)
        }

    def _calculate_creation_confidence(
        self,
        improvement_potential: float,
        feedback_score: float,
        performance: PerformanceMetric,
        similar_skills_count: int
    ) -> float:
        """Calculate confidence score for creating a new skill."""
        base_confidence = improvement_potential * 0.4

        # Positive feedback boosts confidence
        if feedback_score > 0:
            base_confidence += feedback_score * 0.3

        # Low error rate is good
        if performance.error_rate < 0.2:
            base_confidence += 0.2

        # Penalize if too many similar skills exist
        if similar_skills_count > 3:
            base_confidence -= 0.1

        return min(1.0, max(0.0, base_confidence))

    def _assess_improvement_trend(self, skill: Skill) -> float:
        """Assess the improvement trend of a skill."""
        if not skill.improvement_history:
            return 0.5  # Neutral if no history

        recent_improvements = skill.improvement_history[-5:]  # Last 5 improvements
        if not recent_improvements:
            return 0.5

        avg_improvement = sum(r.effectiveness_gain for r in recent_improvements) / len(recent_improvements)
        return min(1.0, max(0.0, avg_improvement + 0.5))  # Normalize to 0-1

    def _calculate_recency_factor(self, skill: Skill, recent_threshold: datetime) -> float:
        """Calculate how recently the skill was used."""
        if not skill.usage_stats.last_used_at:
            return 0.0

        try:
            last_used = datetime.fromisoformat(skill.usage_stats.last_used_at.replace('Z', '+00:00'))
            if last_used >= recent_threshold:
                return 1.0
            else:
                days_since = (datetime.now() - last_used).days
                return max(0.0, 1.0 - days_since / 365.0)  # Decay over year
        except ValueError:
            return 0.0

    def _days_since_last_use(self, skill: Skill) -> int:
        """Calculate days since skill was last used."""
        if not skill.usage_stats.last_used_at:
            return 999  # Very high number for never used

        try:
            last_used = datetime.fromisoformat(skill.usage_stats.last_used_at.replace('Z', '+00:00'))
            return (datetime.now() - last_used).days
        except ValueError:
            return 999

    def _generate_recommendation(self, overall_score: float, skill: Skill) -> str:
        """Generate recommendation based on skill evaluation."""
        if overall_score >= 0.8:
            return "Excellent skill - continue using and consider as template for similar scenarios"
        elif overall_score >= 0.6:
            return "Good skill - monitor performance and consider minor improvements"
        elif overall_score >= 0.4:
            return "Average skill - analyze for improvement opportunities"
        elif overall_score >= 0.2:
            return "Poor skill - consider significant updates or replacement"
        else:
            return "Very poor skill - recommend deprecation or complete redesign"