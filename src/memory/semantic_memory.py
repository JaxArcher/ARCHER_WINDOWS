"""
Semantic Memory System for ARCHER.

Manages long-term knowledge and user preferences.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SemanticMemory:
    """
    Manages ARCHER's semantic memory (knowledge, preferences, facts).

    MVP Implementation:
    - JSON-based storage
    - Category-based organization
    - Simple query interface
    """

    def __init__(self, memory_file: Optional[Path] = None):
        """
        Initialize semantic memory.

        Args:
            memory_file: Path to JSON memory file
        """
        if memory_file is None:
            memory_file = Path("data/semantic_profile.json")

        self.memory_file = memory_file
        self.memory: Dict[str, Any] = self._load_memory()

        logger.info(f"Semantic memory initialized: {memory_file}")

    def _load_memory(self) -> Dict[str, Any]:
        """Load memory from disk."""
        if not self.memory_file.exists():
            logger.info("Creating new semantic memory")
            return self._create_default_memory()

        try:
            with open(self.memory_file, "r") as f:
                memory = json.load(f)
                logger.info(f"Loaded semantic memory ({len(memory)} categories)")
                return memory
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
            return self._create_default_memory()

    def _create_default_memory(self) -> Dict[str, Any]:
        """Create default memory structure."""
        return {
            "user_profile": {
                "name": None,
                "preferences": {},
                "habits": {},
                "health": {},
                "goals": [],
            },
            "facts": {},
            "conversations": {
                "total_interactions": 0,
                "last_interaction": None,
                "topics_discussed": [],
            },
            "skills": {"learned_commands": [], "custom_responses": {}},
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "version": "1.0",
            },
        }

    def save(self):
        """Save memory to disk."""
        try:
            self.memory["metadata"]["last_updated"] = datetime.now().isoformat()

            # Ensure directory exists
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.memory_file, "w") as f:
                json.dump(self.memory, f, indent=2)

            logger.debug("Semantic memory saved")

        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    def store_fact(self, category: str, key: str, value: Any):
        """
        Store a fact in memory.

        Args:
            category: Category (e.g., "user_profile", "preferences")
            key: Fact key
            value: Fact value
        """
        if category not in self.memory:
            self.memory[category] = {}

        # Redact PII from string values
        if isinstance(value, str):
            value = self.redact_pii(value)

        self.memory[category][key] = value
        self.save()

        logger.info(f"Stored fact: {category}.{key} = {value}")

    def get_fact(self, category: str, key: str, default: Any = None) -> Any:
        """
        Retrieve a fact from memory.

        Args:
            category: Category
            key: Fact key
            default: Default value if not found

        Returns:
            Stored value or default
        """
        return self.memory.get(category, {}).get(key, default)

    def update_user_preference(self, preference_key: str, value: Any):
        """Update a user preference."""
        self.store_fact("user_profile", f"preferences.{preference_key}", value)

    def get_user_preferences(self) -> Dict[str, Any]:
        """Get all user preferences."""
        return self.memory.get("user_profile", {}).get("preferences", {})

    def record_interaction(self, topic: Optional[str] = None):
        """Record that an interaction occurred."""
        convos = self.memory.get("conversations", {})
        convos["total_interactions"] = convos.get("total_interactions", 0) + 1
        convos["last_interaction"] = datetime.now().isoformat()

        if topic and topic not in convos.get("topics_discussed", []):
            if "topics_discussed" not in convos:
                convos["topics_discussed"] = []
            convos["topics_discussed"].append(topic)

        self.memory["conversations"] = convos
        self.save()

    def get_context_for_llm(self) -> Dict[str, Any]:
        """
        Get relevant memory context to pass to LLM.

        Returns:
            Dictionary of relevant context
        """
        return {
            "user_name": self.get_fact("user_profile", "name"),
            "preferences": self.get_user_preferences(),
            "interaction_count": self.memory.get("conversations", {}).get(
                "total_interactions", 0
            ),
            "goals": self.memory.get("user_profile", {}).get("goals", []),
        }

    def get_proactive_triggers(self) -> List[Dict[str, Any]]:
        """
        Get proactive triggers based on user profile and context.

        Returns:
            List of trigger dictionaries with conditions and actions
        """
        triggers = []

        # Reminder triggers
        goals = self.memory.get("user_profile", {}).get("goals", [])
        for goal in goals:
            if "deadline" in goal:
                triggers.append(
                    {
                        "type": "reminder",
                        "condition": f"approaching deadline for {goal.get('description', 'goal')}",
                        "action": f"Remind user about: {goal.get('description', 'goal')}",
                        "priority": "medium",
                    }
                )

        # Health triggers
        health = self.memory.get("user_profile", {}).get("health", {})
        if health.get("needs_exercise"):
            triggers.append(
                {
                    "type": "health",
                    "condition": "sedentary for too long",
                    "action": "Suggest exercise break",
                    "priority": "high",
                }
            )

        # Financial triggers
        if (
            self.memory.get("user_profile", {})
            .get("preferences", {})
            .get("finance_monitoring")
        ):
            triggers.append(
                {
                    "type": "finance",
                    "condition": "market hours active",
                    "action": "Check portfolio status",
                    "priority": "low",
                }
            )

        return triggers

    def consolidate_eod(self):
        """
        End-of-day consolidation: merge observations, update preferences/goals.
        """
        logger.info("Running EOD consolidation...")

        # Update interaction summary
        conversations = self.memory.get("conversations", {})
        total_interactions = conversations.get("total_interactions", 0)

        # Analyze interaction patterns
        topics = conversations.get("topics_discussed", [])
        if topics:
            # Update user interests
            interests = self.memory.get("user_profile", {}).get("interests", [])
            for topic in topics:
                if topic not in interests:
                    interests.append(topic)
            self.memory["user_profile"]["interests"] = interests

        # Update goals progress (placeholder)
        goals = self.memory.get("user_profile", {}).get("goals", [])
        # Would analyze progress based on interactions

        # Clean up old data (configurable retention)
        retention_days = int(os.getenv("MEMORY_RETENTION_DAYS", 90))
        # Placeholder - would implement retention logic

        self.save()
        logger.info("EOD consolidation complete")

    def redact_pii(self, text: str) -> str:
        """
        Redact personally identifiable information from text.

        Args:
            text: Text to redact

        Returns:
            Redacted text
        """
        import re

        # Patterns for PII
        pii_patterns = {
            r"\b\d{3}-\d{2}-\d{4}\b": "[REDACTED_SSN]",  # SSN
            r"\b\d{4} \d{4} \d{4} \d{4}\b": "[REDACTED_CARD]",  # Credit card
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b": "[REDACTED_EMAIL]",  # Email
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b": "[REDACTED_PHONE]",  # Phone
            r"\b\d{1,5}\s\w+\s\w+\b": "[REDACTED_ADDRESS]",  # Address (simple)
            r"\b(?:sk-|pk_|api_key|apikey|token|secret)[a-zA-Z0-9_-]{20,}\b": "[REDACTED_API_KEY]",  # API keys
            r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b": "[REDACTED_IPV4]",  # IPv4
            r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b": "[REDACTED_IPV6]",  # IPv6
            r"/home/[^/\s]+(?:/[^/\s]*)*": "[REDACTED_USER_PATH_UNIX]",  # Unix user paths
            r"C:\\Users\\[^\\]+(?:\\[^\\]*)*": "[REDACTED_USER_PATH_WIN]",  # Windows user paths
        }

        redacted = text
        for pattern, replacement in pii_patterns.items():
            redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)

        return redacted

    def __repr__(self) -> str:
        categories = len(self.memory)
        interactions = self.memory.get("conversations", {}).get("total_interactions", 0)
        return f"SemanticMemory(categories={categories}, interactions={interactions})"
