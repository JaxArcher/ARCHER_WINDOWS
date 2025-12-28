"""
Episodic Memory System for ARCHER.

Stores time-series events, conversations, and observations for recall and analysis.
"""

import json
import logging
import os
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EpisodicMemory:
    """
    Episodic memory for storing and retrieving time-series events.

    Features:
    - Event storage with timestamps and metadata
    - Temporal queries (recent events, time ranges)
    - Event clustering and summarization
    - Integration with semantic memory
    """

    def __init__(self, memory_file: Optional[Path] = None):
        if memory_file is None:
            memory_file = Path("data/episodic_memory.json")

        self.memory_file = memory_file
        self.events: List[Dict[str, Any]] = self._load_memory()

        # Retention settings
        self.max_events = int(os.getenv("MAX_EPISODIC_EVENTS", 10000))
        self.retention_days = int(os.getenv("EPISODIC_RETENTION_DAYS", 30))

        logger.info(f"Episodic memory initialized: {len(self.events)} events")

    def redact_pii(self, text: str) -> str:
        """
        Redact personally identifiable information from text.
        """
        import re

        pii_patterns = {
            r"\b\d{3}-\d{2}-\d{4}\b": "[REDACTED_SSN]",
            r"\b\d{4} \d{4} \d{4} \d{4}\b": "[REDACTED_CARD]",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b": "[REDACTED_EMAIL]",
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b": "[REDACTED_PHONE]",
            r"\b\d{1,5}\s\w+\s\w+\b": "[REDACTED_ADDRESS]",
            r"\b(?:sk-|pk_|api_key|apikey|token|secret)[a-zA-Z0-9_-]{20,}\b": "[REDACTED_API_KEY]",
            r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b": "[REDACTED_IPV4]",
            r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b": "[REDACTED_IPV6]",
            r"/home/[^/\s]+(?:/[^/\s]*)*": "[REDACTED_USER_PATH_UNIX]",
            r"C:\\Users\\[^\\]+(?:\\[^\\]*)*": "[REDACTED_USER_PATH_WIN]",
        }

        redacted = text
        for pattern, replacement in pii_patterns.items():
            redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)

        return redacted

    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact PII from dictionary values."""
        redacted = {}
        for k, v in data.items():
            if isinstance(v, str):
                redacted[k] = self.redact_pii(v)
            elif isinstance(v, dict):
                redacted[k] = self._redact_dict(v)
            elif isinstance(v, list):
                redacted[k] = [
                    self.redact_pii(item) if isinstance(item, str) else item
                    for item in v
                ]
            else:
                redacted[k] = v
        return redacted

    def _load_memory(self) -> List[Dict[str, Any]]:
        """Load episodic memory from disk."""
        if not self.memory_file.exists():
            logger.info("Creating new episodic memory")
            return []

        try:
            with open(self.memory_file, "r") as f:
                events = json.load(f)
                logger.info(f"Loaded episodic memory: {len(events)} events")
                return events
        except Exception as e:
            logger.error(f"Failed to load episodic memory: {e}")
            return []

    def save(self):
        """Save episodic memory to disk."""
        try:
            # Clean old events
            self._cleanup_old_events()

            # Ensure directory exists
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.memory_file, "w") as f:
                json.dump(self.events, f, indent=2, default=str)

            logger.debug(f"Episodic memory saved: {len(self.events)} events")

        except Exception as e:
            logger.error(f"Failed to save episodic memory: {e}")

    def _cleanup_old_events(self):
        """Remove events older than retention period."""
        cutoff_time = time.time() - (self.retention_days * 24 * 60 * 60)

        original_count = len(self.events)
        self.events = [e for e in self.events if e.get("timestamp", 0) > cutoff_time]

        if len(self.events) < original_count:
            logger.info(f"Cleaned up {original_count - len(self.events)} old events")

        # Enforce max events limit
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]
            logger.info(f"Trimmed events to max limit: {self.max_events}")

    def store_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Store an episodic event.

        Args:
            event_type: Type of event (e.g., "conversation", "observation", "action")
            data: Event data
            metadata: Optional metadata (tags, importance, etc.)
        """
        # Redact PII from data and metadata
        redacted_data = self._redact_dict(data)
        redacted_metadata = self._redact_dict(metadata) if metadata else {}

        event = {
            "event_id": f"{event_type}_{int(time.time() * 1000)}",
            "event_type": event_type,
            "timestamp": time.time(),
            "data": redacted_data,
            "metadata": redacted_metadata,
        }

        self.events.append(event)
        self.save()

        logger.debug(f"Stored episodic event: {event_type}")

    def get_recent_events(
        self, hours: int = 24, event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent events within time window.

        Args:
            hours: Number of hours to look back
            event_type: Filter by event type (optional)

        Returns:
            List of recent events
        """
        cutoff_time = time.time() - (hours * 60 * 60)

        events = [e for e in self.events if e["timestamp"] > cutoff_time]

        if event_type:
            events = [e for e in events if e["event_type"] == event_type]

        return sorted(events, key=lambda x: x["timestamp"], reverse=True)

    def get_events_by_type(
        self, event_type: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get events of a specific type."""
        events = [e for e in self.events if e["event_type"] == event_type]
        return sorted(events, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def search_events(
        self, query: str, event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search events by content.

        Args:
            query: Search query (case-insensitive substring match)
            event_type: Filter by event type (optional)

        Returns:
            Matching events
        """
        query_lower = query.lower()
        matching_events = []

        for event in self.events:
            if event_type and event["event_type"] != event_type:
                continue

            # Search in event data
            data_str = json.dumps(event["data"]).lower()
            if query_lower in data_str:
                matching_events.append(event)

        return sorted(matching_events, key=lambda x: x["timestamp"], reverse=True)

    def get_conversation_history(
        self, user_id: str = "default", limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a user."""
        conversations = self.get_events_by_type("conversation", limit * 2)

        # Filter by user if needed
        user_conversations = [
            c for c in conversations if c["data"].get("user_id") == user_id
        ]

        return user_conversations[:limit]

    def get_daily_summary(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary of events for a specific date.

        Args:
            date: Date in YYYY-MM-DD format (default: today)

        Returns:
            Daily summary statistics
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # Parse date to timestamp range
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        start_timestamp = date_obj.timestamp()
        end_timestamp = (date_obj + timedelta(days=1)).timestamp()

        # Get events for the date
        day_events = [
            e for e in self.events if start_timestamp <= e["timestamp"] < end_timestamp
        ]

        # Summarize by type
        type_counts = {}
        for event in day_events:
            event_type = event["event_type"]
            type_counts[event_type] = type_counts.get(event_type, 0) + 1

        # Get key metrics
        conversations = len(
            [e for e in day_events if e["event_type"] == "conversation"]
        )
        observations = len([e for e in day_events if e["event_type"] == "observation"])
        actions = len([e for e in day_events if e["event_type"] == "action"])

        return {
            "date": date,
            "total_events": len(day_events),
            "event_types": type_counts,
            "conversations": conversations,
            "observations": observations,
            "actions": actions,
            "most_active_hour": self._get_most_active_hour(day_events),
        }

    def _get_most_active_hour(self, events: List[Dict[str, Any]]) -> Optional[int]:
        """Get the hour with most events."""
        if not events:
            return None

        hour_counts = {}
        for event in events:
            hour = datetime.fromtimestamp(event["timestamp"]).hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        return (
            max(hour_counts.keys(), key=lambda x: hour_counts[x])
            if hour_counts
            else None
        )

    def get_patterns(self, days: int = 7) -> Dict[str, Any]:
        """
        Analyze patterns in recent events.

        Args:
            days: Number of days to analyze

        Returns:
            Pattern analysis
        """
        recent_events = self.get_recent_events(hours=days * 24)

        if not recent_events:
            return {"status": "no_data"}

        # Analyze event frequency by type
        type_frequency = {}
        for event in recent_events:
            event_type = event["event_type"]
            type_frequency[event_type] = type_frequency.get(event_type, 0) + 1

        # Analyze temporal patterns
        hourly_pattern = {}
        for event in recent_events:
            hour = datetime.fromtimestamp(event["timestamp"]).hour
            hourly_pattern[hour] = hourly_pattern.get(hour, 0) + 1

        return {
            "period_days": days,
            "total_events": len(recent_events),
            "type_frequency": type_frequency,
            "hourly_pattern": hourly_pattern,
            "most_common_type": max(
                type_frequency.keys(), key=lambda x: type_frequency[x]
            )
            if type_frequency
            else None,
            "most_active_hour": max(
                hourly_pattern.keys(), key=lambda x: hourly_pattern[x]
            )
            if hourly_pattern
            else None,
        }

    def __len__(self) -> int:
        """Return number of stored events."""
        return len(self.events)

    def __repr__(self) -> str:
        return f"EpisodicMemory(events={len(self.events)}, file={self.memory_file})"
