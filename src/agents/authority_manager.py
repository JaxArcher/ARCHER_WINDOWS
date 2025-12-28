"""
ARCHER Authority Manager - Authority Mode State Machine

Manages the system's authority levels and escalation protocols.
Implements graduated response to uncertainty and risk.
"""

import time
import logging
import threading
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import statistics

from src.events.bus import bus
from src.performance_monitor import performance_monitor
from src.agents.governance import system_contract

logger = logging.getLogger(__name__)


class AuthorityLevel(Enum):
    """System authority levels from passive to autonomous."""

    PASSIVE = "passive"  # Only respond to explicit commands
    OBSERVANT = "observant"  # Monitor and suggest, don't act
    ASSISTIVE = "assistive"  # Provide active assistance with confirmation
    AUTONOMOUS = "autonomous"  # Act independently within safe boundaries
    EMERGENCY = "emergency"  # Override safety for critical situations


class AuthorityTrigger(Enum):
    """Triggers that can change authority level."""

    USER_REQUEST = "user_request"  # Explicit user permission
    CONFIDENCE_HIGH = "confidence_high"  # High confidence in assessment
    RISK_LOW = "risk_low"  # Low risk situation
    TIME_CRITICAL = "time_critical"  # Time-sensitive situation
    PATTERN_RECOGNIZED = "pattern_recognized"  # Recognized user pattern
    SYSTEM_HEALTH = "system_health"  # System health change
    EXTERNAL_THREAT = "external_threat"  # Security threat detected
    GOVERNANCE_VIOLATION = "governance_violation"  # Contract violation


class AuthorityState:
    """Represents the current authority state."""

    def __init__(
        self,
        level: AuthorityLevel,
        confidence: float = 0.5,
        triggers: List[AuthorityTrigger] = None,
        expires_at: float = None,
    ):
        self.level = level
        self.confidence = confidence
        self.triggers = triggers or []
        self.created_at = time.time()
        self.expires_at = expires_at
        self.action_count = 0
        self.violation_count = 0

    def is_expired(self) -> bool:
        """Check if this authority state has expired."""
        return self.expires_at and time.time() > self.expires_at

    def can_perform_action(self, action_type: str, risk_level: str) -> bool:
        """Check if current authority allows a specific action."""

        # Emergency mode allows everything
        if self.level == AuthorityLevel.EMERGENCY:
            return True

        # Passive mode only allows explicit user commands
        if self.level == AuthorityLevel.PASSIVE:
            return action_type == "user_command"

        # Observant mode only allows suggestions
        if self.level == AuthorityLevel.OBSERVANT:
            return action_type in ["suggest", "notify", "observe"]

        # Assistive mode allows helpful actions with confirmation
        if self.level == AuthorityLevel.ASSISTIVE:
            low_risk_actions = ["remind", "schedule", "search_local", "analyze_safe"]
            return action_type in low_risk_actions or risk_level == "low"

        # Autonomous mode allows independent actions within boundaries
        if self.level == AuthorityLevel.AUTONOMOUS:
            # Check against governance contract
            governance_check = system_contract.validate_action(
                {
                    "type": action_type,
                    "parameters": {"risk_level": risk_level},
                    "context": {"authority_level": self.level.value},
                }
            )
            return governance_check["approved"]

        return False

    def record_action(self, action_type: str, success: bool):
        """Record an action performed under this authority."""
        self.action_count += 1
        if not success:
            self.violation_count += 1

    def get_effectiveness_score(self) -> float:
        """Calculate effectiveness score for this authority state."""
        if self.action_count == 0:
            return 0.5  # Neutral score for no actions

        success_rate = (self.action_count - self.violation_count) / self.action_count
        return success_rate


class AuthorityManager:
    """
    Manages system authority levels and escalation protocols.

    Implements a state machine that adjusts authority based on context,
    confidence levels, and system conditions.
    """

    def __init__(self):
        self.current_state: AuthorityState = AuthorityState(AuthorityLevel.OBSERVANT)
        self.state_history: List[AuthorityState] = [self.current_state]
        self._lock = threading.Lock()

        # Authority escalation policies
        self.escalation_policies = self._init_escalation_policies()

        # Confidence tracking
        self.confidence_history = []
        self.confidence_window = 10  # Track last 10 confidence measurements

        # Initialize monitoring
        self._init_authority_monitoring()

        logger.info(
            f"Authority Manager initialized at {self.current_state.level.value} level"
        )

    def _init_escalation_policies(self) -> Dict[AuthorityTrigger, Dict]:
        """Initialize authority escalation policies."""

        return {
            AuthorityTrigger.USER_REQUEST: {
                "target_level": AuthorityLevel.ASSISTIVE,
                "duration": 1800,  # 30 minutes
                "confidence_threshold": 0.3,
            },
            AuthorityTrigger.CONFIDENCE_HIGH: {
                "target_level": AuthorityLevel.AUTONOMOUS,
                "duration": 600,  # 10 minutes
                "confidence_threshold": 0.8,
            },
            AuthorityTrigger.RISK_LOW: {
                "target_level": AuthorityLevel.ASSISTIVE,
                "duration": 300,  # 5 minutes
                "confidence_threshold": 0.5,
            },
            AuthorityTrigger.TIME_CRITICAL: {
                "target_level": AuthorityLevel.AUTONOMOUS,
                "duration": 120,  # 2 minutes
                "confidence_threshold": 0.6,
            },
            AuthorityTrigger.PATTERN_RECOGNIZED: {
                "target_level": AuthorityLevel.ASSISTIVE,
                "duration": 900,  # 15 minutes
                "confidence_threshold": 0.7,
            },
            AuthorityTrigger.SYSTEM_HEALTH: {
                "conditions": {
                    "healthy": AuthorityLevel.AUTONOMOUS,
                    "degraded": AuthorityLevel.ASSISTIVE,
                    "critical": AuthorityLevel.OBSERVANT,
                }
            },
            AuthorityTrigger.EXTERNAL_THREAT: {
                "target_level": AuthorityLevel.PASSIVE,
                "duration": 3600,  # 1 hour
                "confidence_threshold": 0.9,
            },
            AuthorityTrigger.GOVERNANCE_VIOLATION: {
                "target_level": AuthorityLevel.OBSERVANT,
                "duration": 1800,  # 30 minutes
                "confidence_threshold": 0.1,
            },
        }

    def _init_authority_monitoring(self):
        """Set up authority monitoring and event handling."""
        bus.subscribe("authority.escalation_request", self._handle_escalation_request)
        bus.subscribe(
            "authority.deescalation_request", self._handle_deescalation_request
        )
        bus.subscribe("system.health_changed", self._handle_health_change)
        bus.subscribe("governance.violation", self._handle_governance_violation)
        bus.subscribe("performance.confidence_update", self._handle_confidence_update)

    def request_authority_escalation(
        self, trigger: AuthorityTrigger, confidence: float = 0.5, context: Dict = None
    ) -> bool:
        """
        Request escalation of authority level.

        Args:
            trigger: The trigger causing the escalation request
            confidence: Confidence level in the escalation decision
            context: Additional context for the decision

        Returns:
            True if escalation was approved and executed
        """
        with self._lock:
            policy = self.escalation_policies.get(trigger)
            if not policy:
                logger.warning(f"No policy for trigger: {trigger.value}")
                return False

            # Check confidence threshold
            if confidence < policy.get("confidence_threshold", 0.5):
                logger.info(
                    f"Escalation request denied: confidence {confidence} below threshold"
                )
                return False

            # Check system health
            health_status = performance_monitor.get_health_status()
            if health_status["overall"] == "critical":
                logger.warning("Escalation denied: system health critical")
                return False

            # Determine target level
            if "conditions" in policy:
                # Health-based escalation
                current_health = health_status["overall"]
                target_level = policy["conditions"].get(
                    current_health, self.current_state.level
                )
            else:
                target_level = policy["target_level"]

            # Check if escalation is actually needed
            current_priority = self._get_level_priority(self.current_state.level)
            target_priority = self._get_level_priority(target_level)

            if target_priority <= current_priority:
                logger.info(f"Escalation not needed: current level sufficient")
                return False

            # Execute escalation
            return self._escalate_authority(
                target_level, trigger, policy.get("duration"), confidence
            )

    def _escalate_authority(
        self,
        target_level: AuthorityLevel,
        trigger: AuthorityTrigger,
        duration: float = None,
        confidence: float = 0.5,
    ) -> bool:
        """Execute authority escalation."""

        expires_at = time.time() + duration if duration else None

        new_state = AuthorityState(
            level=target_level,
            confidence=confidence,
            triggers=[trigger],
            expires_at=expires_at,
        )

        old_level = self.current_state.level
        self.current_state = new_state
        self.state_history.append(new_state)

        # Keep only last 50 states
        if len(self.state_history) > 50:
            self.state_history.pop(0)

        logger.info(
            f"Authority escalated: {old_level.value} → {target_level.value} "
            f"(trigger: {trigger.value}, duration: {duration}s)"
        )

        bus.publish(
            "authority.level_changed",
            {
                "old_level": old_level.value,
                "new_level": target_level.value,
                "trigger": trigger.value,
                "confidence": confidence,
                "expires_at": expires_at,
                "timestamp": time.time(),
            },
        )

        return True

    def deescalate_authority(self, reason: str = "automatic"):
        """De-escalate authority level toward safer defaults."""
        with self._lock:
            # De-escalate one level at a time
            current_level = self.current_state.level

            if current_level == AuthorityLevel.EMERGENCY:
                new_level = AuthorityLevel.AUTONOMOUS
            elif current_level == AuthorityLevel.AUTONOMOUS:
                new_level = AuthorityLevel.ASSISTIVE
            elif current_level == AuthorityLevel.ASSISTIVE:
                new_level = AuthorityLevel.OBSERVANT
            else:
                # Already at minimum safe level
                return False

            new_state = AuthorityState(
                level=new_level,
                confidence=0.5,
                triggers=[AuthorityTrigger.USER_REQUEST],  # Default safe trigger
            )

            old_level = self.current_state.level
            self.current_state = new_state
            self.state_history.append(new_state)

            logger.info(
                f"Authority de-escalated: {old_level.value} → {new_level.value} ({reason})"
            )

            bus.publish(
                "authority.level_changed",
                {
                    "old_level": old_level.value,
                    "new_level": new_level.value,
                    "reason": reason,
                    "timestamp": time.time(),
                },
            )

            return True

    def check_action_authority(
        self, action_type: str, risk_level: str = "medium", context: Dict = None
    ) -> Dict[str, Any]:
        """
        Check if an action is authorized under current authority level.

        Returns detailed authorization information.
        """
        with self._lock:
            # Check if current state is expired
            if self.current_state.is_expired():
                logger.info("Authority state expired, de-escalating")
                self.deescalate_authority("state_expired")

            authorized = self.current_state.can_perform_action(action_type, risk_level)

            # Additional governance check
            governance_check = system_contract.validate_action(
                {
                    "type": action_type,
                    "parameters": {"risk_level": risk_level},
                    "context": context or {},
                }
            )

            final_authorized = authorized and governance_check["approved"]

            result = {
                "authorized": final_authorized,
                "authority_level": self.current_state.level.value,
                "confidence": self.current_state.confidence,
                "governance_check": governance_check,
                "risk_assessment": risk_level,
                "expires_at": self.current_state.expires_at,
                "timestamp": time.time(),
            }

            if not final_authorized:
                logger.info(
                    f"Action not authorized: {action_type} (risk: {risk_level})"
                )
                bus.publish(
                    "authority.action_denied",
                    {
                        "action_type": action_type,
                        "risk_level": risk_level,
                        "reason": "insufficient_authority"
                        if not authorized
                        else "governance_violation",
                        "authority_level": self.current_state.level.value,
                    },
                )

            return result

    def record_action_result(
        self, action_type: str, success: bool, context: Dict = None
    ):
        """Record the result of an action for authority learning."""
        with self._lock:
            self.current_state.record_action(action_type, success)

            # Update confidence based on action results
            effectiveness = self.current_state.get_effectiveness_score()

            # Adjust confidence based on recent performance
            if success:
                self.current_state.confidence = min(
                    1.0, self.current_state.confidence + 0.1
                )
            else:
                self.current_state.confidence = max(
                    0.0, self.current_state.confidence - 0.2
                )

            # Publish action result
            bus.publish(
                "authority.action_recorded",
                {
                    "action_type": action_type,
                    "success": success,
                    "effectiveness": effectiveness,
                    "new_confidence": self.current_state.confidence,
                    "context": context,
                    "timestamp": time.time(),
                },
            )

    def _get_level_priority(self, level: AuthorityLevel) -> int:
        """Get numeric priority for authority level comparison."""
        priorities = {
            AuthorityLevel.PASSIVE: 0,
            AuthorityLevel.OBSERVANT: 1,
            AuthorityLevel.ASSISTIVE: 2,
            AuthorityLevel.AUTONOMOUS: 3,
            AuthorityLevel.EMERGENCY: 4,
        }
        return priorities[level]

    def _handle_escalation_request(self, event_data: Dict):
        """Handle authority escalation requests."""
        trigger = AuthorityTrigger(event_data.get("trigger", "user_request"))
        confidence = event_data.get("confidence", 0.5)
        context = event_data.get("context", {})

        self.request_authority_escalation(trigger, confidence, context)

    def _handle_deescalation_request(self, event_data: Dict):
        """Handle authority de-escalation requests."""
        reason = event_data.get("reason", "requested")
        self.deescalate_authority(reason)

    def _handle_health_change(self, event_data: Dict):
        """Handle system health changes."""
        health_status = event_data.get("status", "unknown")

        if health_status == "critical":
            self.request_authority_escalation(AuthorityTrigger.SYSTEM_HEALTH, 0.9)
        elif health_status == "healthy":
            # Allow potential escalation if conditions are good
            self._evaluate_auto_escalation()

    def _handle_governance_violation(self, event_data: Dict):
        """Handle governance violations."""
        self.request_authority_escalation(AuthorityTrigger.GOVERNANCE_VIOLATION, 0.8)

    def _handle_confidence_update(self, event_data: Dict):
        """Handle confidence updates for potential escalation."""
        confidence = event_data.get("confidence", 0.5)

        # Track confidence history
        self.confidence_history.append(confidence)
        if len(self.confidence_history) > self.confidence_window:
            self.confidence_history.pop(0)

        # Check for sustained high confidence
        if len(self.confidence_history) >= 5:
            avg_confidence = statistics.mean(self.confidence_history[-5:])
            if avg_confidence > 0.8:
                self.request_authority_escalation(
                    AuthorityTrigger.CONFIDENCE_HIGH, avg_confidence
                )

    def _evaluate_auto_escalation(self):
        """Evaluate conditions for automatic authority escalation."""
        # Check various conditions for potential escalation
        health_status = performance_monitor.get_health_status()

        if health_status["overall"] == "healthy":
            # Check confidence levels
            if self.confidence_history:
                recent_confidence = (
                    statistics.mean(self.confidence_history[-3:])
                    if len(self.confidence_history) >= 3
                    else 0.5
                )
                if recent_confidence > 0.7:
                    self.request_authority_escalation(
                        AuthorityTrigger.CONFIDENCE_HIGH, recent_confidence
                    )

    def get_authority_status(self) -> Dict[str, Any]:
        """Get comprehensive authority status."""
        with self._lock:
            return {
                "current_level": self.current_state.level.value,
                "confidence": self.current_state.confidence,
                "expires_at": self.current_state.expires_at,
                "action_count": self.current_state.action_count,
                "violation_count": self.current_state.violation_count,
                "effectiveness_score": self.current_state.get_effectiveness_score(),
                "triggers": [t.value for t in self.current_state.triggers],
                "system_health": performance_monitor.get_health_status(),
                "governance_status": system_contract.get_contract_status(),
                "state_history_length": len(self.state_history),
                "timestamp": time.time(),
            }


# Global authority manager instance
authority_manager = AuthorityManager()
