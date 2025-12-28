"""
ARCHER Action Ledger - Proactive Action Logging & Accountability

Maintains a comprehensive ledger of all proactive actions taken by the system,
enabling accountability, learning, and user transparency.
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import json
import os

from src.events.bus import bus

logger = logging.getLogger(__name__)


def redact_pii(text: str) -> str:
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


def _redact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively redact PII from dictionary values."""
    redacted = {}
    for k, v in data.items():
        if isinstance(v, str):
            redacted[k] = redact_pii(v)
        elif isinstance(v, dict):
            redacted[k] = _redact_dict(v)
        elif isinstance(v, list):
            redacted[k] = [
                redact_pii(item) if isinstance(item, str) else item for item in v
            ]
        else:
            redacted[k] = v
    return redacted


@dataclass
class ActionRecord:
    """Represents a logged action in the ledger."""

    action_id: str
    timestamp: float
    agent: str
    action_type: str
    description: str
    context: Dict[str, Any]
    authority_level: str
    governance_check: Dict[str, Any]
    outcome: Optional[str] = None
    effectiveness_score: Optional[float] = None
    user_feedback: Optional[str] = None
    resolved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionRecord":
        """Create from dictionary."""
        return cls(**data)

    def is_resolved(self) -> bool:
        """Check if action has been resolved/reviewed."""
        return self.resolved_at is not None

    def get_duration(self) -> Optional[float]:
        """Get action duration if resolved."""
        if self.resolved_at:
            return self.resolved_at - self.timestamp
        return None


class ActionLedger:
    """
    Comprehensive ledger of all proactive system actions.

    Maintains accountability, enables learning from past actions,
    and provides transparency to users about system behavior.
    """

    def __init__(
        self, max_records: int = 10000, persistence_file: str = "action_ledger.json"
    ):
        self.records: List[ActionRecord] = []
        self.agent_summaries: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.max_records = max_records
        self.persistence_file = os.path.join("data", persistence_file)
        self._lock = threading.Lock()

        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)

        # Load existing records
        self._load_ledger()

        # Initialize ledger monitoring
        self._init_ledger_monitoring()

        logger.info(
            f"Action Ledger initialized with {len(self.records)} existing records"
        )

    def _init_ledger_monitoring(self):
        """Set up ledger event monitoring."""
        bus.subscribe("authority.action_recorded", self._handle_action_recorded)
        bus.subscribe(
            "supervisor.execution_completed", self._handle_execution_completed
        )
        bus.subscribe("intervention.triggered", self._handle_intervention_triggered)
        bus.subscribe("user.feedback_received", self._handle_user_feedback)

    def log_action(
        self,
        agent: str,
        action_type: str,
        description: str,
        context: Dict = None,
        authority_level: str = "unknown",
        governance_check: Dict = None,
    ) -> str:
        """
        Log a new action in the ledger.

        Returns the action ID.
        """
        with self._lock:
            action_id = f"{agent}_{action_type}_{int(time.time())}_{len(self.records)}"

            # Redact PII from description and context
            redacted_description = redact_pii(description)
            redacted_context = _redact_dict(context) if context else {}
            redacted_governance = (
                _redact_dict(governance_check) if governance_check else {}
            )

            record = ActionRecord(
                action_id=action_id,
                timestamp=time.time(),
                agent=agent,
                action_type=action_type,
                description=redacted_description,
                context=redacted_context,
                authority_level=authority_level,
                governance_check=redacted_governance,
            )

            self.records.append(record)

            # Maintain max records limit
            if len(self.records) > self.max_records:
                self.records.pop(0)  # Remove oldest

            # Update agent summary
            self._update_agent_summary(agent, action_type, "logged")

            # Persist to disk periodically (every 10 actions)
            if len(self.records) % 10 == 0:
                self._persist_ledger()

            logger.debug(f"Action logged: {action_id} ({agent}: {action_type})")

            return action_id

    def resolve_action(
        self,
        action_id: str,
        outcome: str,
        effectiveness_score: Optional[float] = None,
        user_feedback: Optional[str] = None,
    ):
        """Resolve an action with outcome information."""
        with self._lock:
            for record in self.records:
                if record.action_id == action_id:
                    record.outcome = outcome
                    record.effectiveness_score = effectiveness_score
                    record.user_feedback = user_feedback
                    record.resolved_at = time.time()

                    # Update agent summary
                    self._update_agent_summary(
                        record.agent, record.action_type, "resolved"
                    )

                    logger.info(f"Action resolved: {action_id} (outcome: {outcome})")

                    # Publish resolution event
                    bus.publish(
                        "ledger.action_resolved",
                        {
                            "action_id": action_id,
                            "outcome": outcome,
                            "effectiveness_score": effectiveness_score,
                            "user_feedback": user_feedback,
                        },
                    )

                    break

    def get_action_history(
        self,
        agent: str = None,
        action_type: str = None,
        limit: int = 100,
        resolved_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get action history with optional filtering."""
        with self._lock:
            filtered_records = self.records

            if agent:
                filtered_records = [r for r in filtered_records if r.agent == agent]

            if action_type:
                filtered_records = [
                    r for r in filtered_records if r.action_type == action_type
                ]

            if resolved_only:
                filtered_records = [r for r in filtered_records if r.is_resolved()]

            # Return most recent first
            return [r.to_dict() for r in filtered_records[-limit:]]

    def get_agent_summary(self, agent: str) -> Dict[str, Any]:
        """Get summary statistics for an agent."""
        with self._lock:
            return self.agent_summaries.get(agent, {}).copy()

    def get_system_summary(self) -> Dict[str, Any]:
        """Get system-wide action summary."""
        with self._lock:
            total_actions = len(self.records)
            resolved_actions = len([r for r in self.records if r.is_resolved()])
            unresolved_actions = total_actions - resolved_actions

            # Calculate effectiveness scores
            effectiveness_scores = [
                r.effectiveness_score
                for r in self.records
                if r.effectiveness_score is not None
            ]

            avg_effectiveness = (
                statistics.mean(effectiveness_scores) if effectiveness_scores else 0.0
            )

            # Action type distribution
            action_types = defaultdict(int)
            for record in self.records:
                action_types[record.action_type] += 1

            # Agent distribution
            agents = defaultdict(int)
            for record in self.records:
                agents[record.agent] += 1

            return {
                "total_actions": total_actions,
                "resolved_actions": resolved_actions,
                "unresolved_actions": unresolved_actions,
                "resolution_rate": resolved_actions / total_actions
                if total_actions > 0
                else 0.0,
                "average_effectiveness": avg_effectiveness,
                "action_type_distribution": dict(action_types),
                "agent_distribution": dict(agents),
                "timestamp": time.time(),
            }

    def _update_agent_summary(self, agent: str, action_type: str, event_type: str):
        """Update agent summary statistics."""
        summary = self.agent_summaries[agent]

        # Initialize counters if needed
        if "total_actions" not in summary:
            summary.update(
                {
                    "total_actions": 0,
                    "resolved_actions": 0,
                    "unresolved_actions": 0,
                    "action_types": defaultdict(int),
                    "effectiveness_scores": [],
                    "last_action": None,
                }
            )

        if event_type == "logged":
            summary["total_actions"] += 1
            summary["unresolved_actions"] += 1
            summary["action_types"][action_type] += 1
            summary["last_action"] = time.time()

        elif event_type == "resolved":
            summary["resolved_actions"] += 1
            summary["unresolved_actions"] = max(0, summary["unresolved_actions"] - 1)

    def _persist_ledger(self):
        """Persist ledger to disk."""
        try:
            with self._lock:
                data = {
                    "records": [r.to_dict() for r in self.records],
                    "agent_summaries": dict(self.agent_summaries),
                    "metadata": {
                        "created_at": time.time(),
                        "total_records": len(self.records),
                    },
                }

                with open(self.persistence_file, "w") as f:
                    json.dump(data, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Failed to persist ledger: {e}")

    def _load_ledger(self):
        """Load ledger from disk."""
        try:
            if os.path.exists(self.persistence_file):
                with open(self.persistence_file, "r") as f:
                    data = json.load(f)

                # Restore records
                self.records = [
                    ActionRecord.from_dict(r) for r in data.get("records", [])
                ]

                # Restore agent summaries
                summaries_data = data.get("agent_summaries", {})
                for agent, summary in summaries_data.items():
                    self.agent_summaries[agent] = summary
                    # Convert defaultdict back
                    if "action_types" in summary:
                        summary["action_types"] = defaultdict(
                            int, summary["action_types"]
                        )

                logger.info(f"Loaded {len(self.records)} records from ledger")

        except Exception as e:
            logger.error(f"Failed to load ledger: {e}")

    def _handle_action_recorded(self, event_data: Dict):
        """Handle action recorded events."""
        self.log_action(
            agent=event_data.get("agent", "unknown"),
            action_type="authority_action",
            description=f"Authority-driven action: {event_data.get('action_type', 'unknown')}",
            context=event_data,
            authority_level="authority_driven",
        )

    def _handle_execution_completed(self, event_data: Dict):
        """Handle execution completed events."""
        execution_id = event_data.get("execution_id")
        if execution_id:
            outcome = "success" if event_data.get("success", False) else "failure"
            effectiveness = event_data.get("metrics", {}).get("effectiveness", 0.5)

            self.resolve_action(execution_id, outcome, effectiveness)

    def _handle_intervention_triggered(self, event_data: Dict):
        """Handle intervention triggered events."""
        self.log_action(
            agent="intervention_manager",
            action_type="intervention",
            description=event_data.get("description", "Intervention triggered"),
            context=event_data,
            authority_level="intervention",
        )

    def _handle_user_feedback(self, event_data: Dict):
        """Handle user feedback on actions."""
        action_id = event_data.get("action_id")
        feedback = event_data.get("feedback")

        if action_id and feedback:
            # Find and update the record
            with self._lock:
                for record in self.records:
                    if record.action_id == action_id:
                        record.user_feedback = feedback
                        break

    def cleanup_old_records(self, max_age_days: int = 90):
        """Clean up records older than specified days."""
        with self._lock:
            cutoff_time = time.time() - (max_age_days * 24 * 3600)

            old_count = len(self.records)
            self.records = [r for r in self.records if r.timestamp > cutoff_time]

            removed_count = old_count - len(self.records)
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old ledger records")
                self._persist_ledger()


# Global action ledger instance
action_ledger = ActionLedger()
