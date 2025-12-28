"""
ARCHER Intervention Manager - Escalation Logic for Critical Situations

Manages intervention escalation when system detects critical situations
requiring immediate action or human oversight.
"""

import time
import logging
import threading
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from src.events.bus import bus
from src.performance_monitor import performance_monitor
from src.agents.authority_manager import authority_manager

logger = logging.getLogger(__name__)


class InterventionLevel(Enum):
    """Intervention escalation levels."""

    MONITOR = "monitor"  # Just monitor, no action
    ALERT = "alert"  # Alert user but don't intervene
    SUGGEST = "suggest"  # Suggest intervention to user
    INTERVENE = "intervene"  # Take automatic corrective action
    EMERGENCY = "emergency"  # Emergency shutdown/safeguard


class InterventionTrigger(Enum):
    """Triggers that can cause intervention escalation."""

    HEALTH_CRITICAL = "health_critical"
    PERFORMANCE_DEGRADED = "performance_degraded"
    SECURITY_THREAT = "security_threat"
    USER_DISTRESS = "user_distress"
    SYSTEM_OVERLOAD = "system_overload"
    GOVERNANCE_VIOLATION = "governance_violation"
    EXTERNAL_ATTACK = "external_attack"


@dataclass
class Intervention:
    """Represents an active intervention."""

    id: str
    level: InterventionLevel
    trigger: InterventionTrigger
    description: str
    actions_taken: List[str]
    created_at: float
    resolved_at: Optional[float] = None
    effectiveness_score: float = 0.0


class InterventionManager:
    """
    Manages intervention escalation for critical situations.

    Monitors system health and user state, escalating interventions
    when automatic correction is needed or human oversight required.
    """

    def __init__(self):
        self.active_interventions: Dict[str, Intervention] = {}
        self.intervention_history: List[Intervention] = []
        self._lock = threading.Lock()

        # Escalation thresholds
        self.thresholds = {
            "cpu_critical": 95.0,
            "memory_critical": 95.0,
            "response_time_critical": 5000,  # 5 seconds
            "error_rate_critical": 0.5,  # 50%
        }

        # Initialize monitoring
        self._init_intervention_monitoring()

        logger.info("Intervention Manager initialized")

    def _init_intervention_monitoring(self):
        """Set up intervention monitoring."""
        bus.subscribe("performance.alert", self._handle_performance_alert)
        bus.subscribe("system.health_changed", self._handle_health_change)
        bus.subscribe("vision.observation.emotion", self._handle_emotion_observation)
        bus.subscribe("governance.violation", self._handle_governance_violation)

    def evaluate_intervention_needed(
        self, context: Dict[str, Any]
    ) -> Optional[InterventionLevel]:
        """
        Evaluate if intervention is needed based on current context.

        Returns the recommended intervention level or None if no intervention needed.
        """
        health_status = performance_monitor.get_health_status()

        # Check system health
        if health_status["overall"] == "critical":
            return InterventionLevel.EMERGENCY

        # Check performance metrics
        performance_report = performance_monitor.get_performance_report()
        voice_metrics = performance_report["metrics"].get("voice_pipeline_total", {})

        if voice_metrics.get("p95", 0) > self.thresholds["response_time_critical"]:
            return InterventionLevel.INTERVENE

        # Check user emotional state
        emotion_data = context.get("emotion_data", {})
        if (
            emotion_data.get("emotion") in ["fear", "angry"]
            and emotion_data.get("confidence", 0) > 0.8
        ):
            return InterventionLevel.ALERT

        return None

    def trigger_intervention(
        self,
        level: InterventionLevel,
        trigger: InterventionTrigger,
        description: str,
        context: Dict = None,
    ) -> str:
        """
        Trigger a new intervention.

        Returns the intervention ID.
        """
        with self._lock:
            intervention_id = (
                f"intervention_{int(time.time())}_{len(self.active_interventions)}"
            )

            intervention = Intervention(
                id=intervention_id,
                level=level,
                trigger=trigger,
                description=description,
                actions_taken=[],
                created_at=time.time(),
            )

            self.active_interventions[intervention_id] = intervention

            logger.warning(
                f"Intervention triggered: {level.value} ({trigger.value}) - {description}"
            )

            # Execute intervention actions
            self._execute_intervention_actions(intervention, context)

            # Publish intervention event
            bus.publish(
                "intervention.triggered",
                {
                    "intervention_id": intervention_id,
                    "level": level.value,
                    "trigger": trigger.value,
                    "description": description,
                    "timestamp": time.time(),
                },
            )

            return intervention_id

    def _execute_intervention_actions(
        self, intervention: Intervention, context: Dict = None
    ):
        """Execute the appropriate actions for an intervention level."""

        if intervention.level == InterventionLevel.ALERT:
            # Alert user through available channels
            intervention.actions_taken.append("user_alert_sent")
            bus.publish(
                "intervention.user_alert",
                {
                    "message": f"System intervention required: {intervention.description}",
                    "severity": "warning",
                },
            )

        elif intervention.level == InterventionLevel.SUGGEST:
            # Suggest corrective action
            intervention.actions_taken.append("suggestion_made")
            bus.publish(
                "intervention.suggestion",
                {
                    "suggestion": self._generate_suggestion(intervention.trigger),
                    "reason": intervention.description,
                },
            )

        elif intervention.level == InterventionLevel.INTERVENE:
            # Take automatic corrective action
            actions = self._generate_corrective_actions(intervention.trigger)
            for action in actions:
                intervention.actions_taken.append(action)
                self._execute_corrective_action(action, context)

        elif intervention.level == InterventionLevel.EMERGENCY:
            # Emergency shutdown/safeguard
            intervention.actions_taken.append("emergency_shutdown")
            self._execute_emergency_shutdown()

    def _generate_suggestion(self, trigger: InterventionTrigger) -> str:
        """Generate a suggestion based on the intervention trigger."""
        suggestions = {
            InterventionTrigger.HEALTH_CRITICAL: "Consider restarting the system or checking system resources",
            InterventionTrigger.PERFORMANCE_DEGRADED: "System performance is degraded, consider reducing load",
            InterventionTrigger.SECURITY_THREAT: "Security threat detected, please verify system integrity",
            InterventionTrigger.USER_DISTRESS: "User appears distressed, consider checking in",
        }
        return suggestions.get(trigger, "System intervention recommended")

    def _generate_corrective_actions(self, trigger: InterventionTrigger) -> List[str]:
        """Generate corrective actions for intervention."""
        actions = {
            InterventionTrigger.HEALTH_CRITICAL: [
                "reduce_processing_load",
                "clear_memory_cache",
            ],
            InterventionTrigger.PERFORMANCE_DEGRADED: [
                "throttle_background_tasks",
                "optimize_resource_usage",
            ],
            InterventionTrigger.SECURITY_THREAT: [
                "enable_security_mode",
                "audit_recent_actions",
            ],
        }
        return actions.get(trigger, ["log_incident"])

    def _execute_corrective_action(self, action: str, context: Dict = None):
        """Execute a specific corrective action."""
        logger.info(f"Executing corrective action: {action}")

        if action == "reduce_processing_load":
            # Reduce concurrent operations
            bus.publish("system.throttle", {"reason": "intervention"})

        elif action == "clear_memory_cache":
            # Clear non-essential caches
            bus.publish("memory.clear_cache", {"reason": "intervention"})

        elif action == "throttle_background_tasks":
            # Reduce background processing
            bus.publish("system.background_throttle", {"reason": "intervention"})

        elif action == "enable_security_mode":
            # Escalate authority to restrictive
            authority_manager.request_authority_escalation(
                authority_manager.escalation_policies[
                    authority_manager.AuthorityTrigger.EXTERNAL_THREAT
                ]["target_level"],
                0.9,
            )

    def _execute_emergency_shutdown(self):
        """Execute emergency shutdown procedures."""
        logger.critical("EMERGENCY SHUTDOWN INITIATED")

        # Stop all active operations
        bus.publish(
            "system.emergency_shutdown",
            {"reason": "critical_intervention", "timestamp": time.time()},
        )

        # This would trigger system-wide shutdown in a real implementation

    def resolve_intervention(
        self, intervention_id: str, effectiveness_score: float = 0.5
    ):
        """Resolve an active intervention."""
        with self._lock:
            if intervention_id in self.active_interventions:
                intervention = self.active_interventions.pop(intervention_id)
                intervention.resolved_at = time.time()
                intervention.effectiveness_score = effectiveness_score

                self.intervention_history.append(intervention)

                # Keep only last 100 interventions
                if len(self.intervention_history) > 100:
                    self.intervention_history.pop(0)

                logger.info(
                    f"Intervention resolved: {intervention_id} (effectiveness: {effectiveness_score})"
                )

                bus.publish(
                    "intervention.resolved",
                    {
                        "intervention_id": intervention_id,
                        "effectiveness_score": effectiveness_score,
                        "duration": intervention.resolved_at - intervention.created_at,
                    },
                )

    def _handle_performance_alert(self, event_data: Dict):
        """Handle performance alerts."""
        severity = event_data.get("severity", "warning")
        metric = event_data.get("metric", "unknown")

        if severity == "critical":
            self.trigger_intervention(
                InterventionLevel.INTERVENE,
                InterventionTrigger.PERFORMANCE_DEGRADED,
                f"Critical performance issue: {metric}",
                event_data,
            )

    def _handle_health_change(self, event_data: Dict):
        """Handle system health changes."""
        status = event_data.get("status", "unknown")

        if status == "critical":
            self.trigger_intervention(
                InterventionLevel.EMERGENCY,
                InterventionTrigger.HEALTH_CRITICAL,
                "System health critical",
                event_data,
            )

    def _handle_emotion_observation(self, event_data: Dict):
        """Handle emotion observations."""
        emotion = event_data.get("emotion", "unknown")
        confidence = event_data.get("confidence", 0.0)

        if emotion in ["fear", "angry"] and confidence > 0.8:
            self.trigger_intervention(
                InterventionLevel.ALERT,
                InterventionTrigger.USER_DISTRESS,
                f"User emotional distress detected: {emotion}",
                event_data,
            )

    def _handle_governance_violation(self, event_data: Dict):
        """Handle governance violations."""
        self.trigger_intervention(
            InterventionLevel.SUGGEST,
            InterventionTrigger.GOVERNANCE_VIOLATION,
            "Governance violation detected",
            event_data,
        )

    def get_intervention_status(self) -> Dict[str, Any]:
        """Get current intervention status."""
        with self._lock:
            return {
                "active_interventions": len(self.active_interventions),
                "intervention_history": len(self.intervention_history),
                "system_health": performance_monitor.get_health_status(),
                "authority_level": authority_manager.get_authority_status()[
                    "current_level"
                ],
                "timestamp": time.time(),
            }


# Global intervention manager instance
intervention_manager = InterventionManager()
