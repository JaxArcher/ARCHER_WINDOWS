"""
Profile Learning Engine for ARCHER.

Learns about the user from conversations and observations.
"""

import logging
import re
from typing import Dict, Any, Optional
from src.memory.semantic_memory import SemanticMemory

logger = logging.getLogger(__name__)


class ProfileLearner:
    """
    Learns user preferences and characteristics from interactions.

    MVP Implementation:
    - Pattern-based extraction from conversations
    - Integration with semantic memory
    - Simple inference rules
    """

    def __init__(self, memory: SemanticMemory):
        """
        Initialize the profile learner.

        Args:
            memory: Semantic memory instance
        """
        self.memory = memory

        # Pattern matchers for common info
        self.patterns = {
            "name": re.compile(r"(?:my name is|i'm|i am|call me)\s+(\w+)", re.IGNORECASE),
            "location": re.compile(r"(?:i live in|i'm from|i'm in)\s+([A-Za-z\s]+)", re.IGNORECASE),
            "preference": re.compile(r"i (?:like|love|prefer|enjoy)\s+([^.!?]+)", re.IGNORECASE),
            "dislike": re.compile(r"i (?:don't like|hate|dislike)\s+([^.!?]+)", re.IGNORECASE),
            "goal": re.compile(r"(?:i want to|i need to|my goal is to)\s+([^.!?]+)", re.IGNORECASE)
        }

        logger.info("ProfileLearner initialized")

    def process_conversation(self, user_text: str, assistant_response: str = ""):
        """
        Process a conversation turn and extract learnings.

        Args:
            user_text: What the user said
            assistant_response: What ARCHER responded (for context)
        """
        logger.debug(f"Processing conversation: '{user_text[:50]}...'")

        # Extract information using patterns
        extracted = self._extract_patterns(user_text)

        # Store extracted information
        for info_type, value in extracted.items():
            self._store_learned_info(info_type, value)

        # Record the interaction
        self.memory.record_interaction(topic=self._infer_topic(user_text))

    def _extract_patterns(self, text: str) -> Dict[str, str]:
        """Extract information using regex patterns."""
        extracted = {}

        for pattern_name, pattern in self.patterns.items():
            match = pattern.search(text)
            if match:
                value = match.group(1).strip()
                extracted[pattern_name] = value
                logger.info(f"Extracted {pattern_name}: '{value}'")

        return extracted

    def _store_learned_info(self, info_type: str, value: str):
        """Store learned information in semantic memory."""

        if info_type == "name":
            self.memory.store_fact("user_profile", "name", value)

        elif info_type == "location":
            self.memory.store_fact("user_profile", "location", value)

        elif info_type == "preference":
            prefs = self.memory.get_fact("user_profile", "preferences", {})
            if not isinstance(prefs, dict):
                prefs = {}
            prefs[value.lower()] = {"type": "like", "mentioned": True}
            self.memory.store_fact("user_profile", "preferences", prefs)

        elif info_type == "dislike":
            prefs = self.memory.get_fact("user_profile", "preferences", {})
            if not isinstance(prefs, dict):
                prefs = {}
            prefs[value.lower()] = {"type": "dislike", "mentioned": True}
            self.memory.store_fact("user_profile", "preferences", prefs)

        elif info_type == "goal":
            goals = self.memory.get_fact("user_profile", "goals", [])
            if not isinstance(goals, list):
                goals = []
            if value not in goals:
                goals.append(value)
            self.memory.store_fact("user_profile", "goals", goals)

    def _infer_topic(self, text: str) -> str:
        """Infer conversation topic (simple keyword-based)."""
        text_lower = text.lower()

        topics = {
            "weather": ["weather", "temperature", "rain", "sunny", "cold", "hot"],
            "work": ["work", "job", "office", "meeting", "project"],
            "health": ["health", "sick", "doctor", "exercise", "diet"],
            "family": ["family", "mom", "dad", "brother", "sister", "child"],
            "hobby": ["hobby", "game", "sport", "music", "movie", "book"]
        }

        for topic, keywords in topics.items():
            if any(kw in text_lower for kw in keywords):
                return topic

        return "general"

    def get_user_summary(self) -> Dict[str, Any]:
        """
        Get a summary of what ARCHER knows about the user.

        Returns:
            Dictionary with user profile information
        """
        return {
            "name": self.memory.get_fact("user_profile", "name"),
            "location": self.memory.get_fact("user_profile", "location"),
            "preferences": self.memory.get_fact("user_profile", "preferences", {}),
            "goals": self.memory.get_fact("user_profile", "goals", []),
            "total_interactions": self.memory.get_fact("conversations", "total_interactions", 0)
        }
