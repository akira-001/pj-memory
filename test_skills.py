#!/usr/bin/env python3
"""Simple test script for Skills Memory Layer integration."""

import tempfile
from pathlib import Path

# Add src to path for testing
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cognitive_memory.config import CogMemConfig
from cognitive_memory.skills import SkillsManager, PerformanceMetric


def test_skills_basic():
    """Test basic skills functionality."""
    print("=== Testing Skills Memory Layer ===")

    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create basic config
        config_content = f"""
[memory]
dir = "{temp_path / 'memory'}"
max_entries = 1000

[embeddings]
provider = "ollama"
model = "nomic-embed-text"
base_url = "http://localhost:11434"
"""

        config_path = temp_path / "cogmem.toml"
        config_path.write_text(config_content)

        # Load config
        config = CogMemConfig.from_toml(str(config_path))

        # Initialize skills manager
        print("Initializing SkillsManager...")
        skills_manager = SkillsManager(config)

        # Test creating a new skill
        print("Creating new skill...")
        performance = PerformanceMetric(
            effectiveness=0.8,
            user_satisfaction=0.7,
            execution_time=1500.0,
            error_rate=0.1
        )

        new_skill = skills_manager.create_skill_from_context(
            context="Help user respond to important emails efficiently",
            performance=performance,
            user_feedback="Good but could be faster"
        )

        print(f"Created skill: {new_skill.name}")
        print(f"  ID: {new_skill.id}")
        print(f"  Category: {new_skill.category}")
        print(f"  Effectiveness: {new_skill.usage_stats.average_effectiveness}")

        # Test searching skills
        print("\nSearching skills...")
        found_skills = skills_manager.search_skills("email", top_k=5)
        print(f"Found {len(found_skills)} skills for 'email' query")

        # Test skill stats
        print("\nGetting skill stats...")
        stats = skills_manager.get_skill_stats()
        print(f"Total skills: {stats['total_skills']}")
        print(f"Average effectiveness: {stats['average_effectiveness']:.3f}")

        print("\n=== Skills test completed successfully! ===")


if __name__ == "__main__":
    try:
        test_skills_basic()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)