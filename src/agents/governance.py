"""
ARCHER System Governance - Core System Contract

Defines the fundamental boundaries, safety protocols, and operational constraints
for the ARCHER autonomous assistant system. This implements the "System Contract"
that governs all agent behavior and system operations.
"""

import time
import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Set
import threading

from src.events.bus import bus
from src.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


class SystemBoundary(Enum):
    """Fundamental system boundaries that cannot be violated."""

    # Safety Boundaries
    NO_HARM = "no_harm"  # Never cause physical/psychological harm
    NO_UNAUTHORIZED_ACCESS = "no_unauthorized"  # No unauthorized system/network access
    NO_DATA_EXPOSURE = "no_data_exposure"  # Never expose sensitive user data
    NO_FINANCIAL_RISK = "no_financial_risk"  # No high-risk financial operations without explicit consent

    # Operational Boundaries
    LOCAL_FIRST = "local_first"  # Prefer local processing over external calls
    USER_CONSENT_REQUIRED = (
        "consent_required"  # Major actions require explicit user consent
    )
    AUDITABLE_ACTIONS = "auditable_actions"  # All significant actions must be logged
    RESOURCE_LIMITED = "resource_limited"  # Respect system resource constraints

    # Ethical Boundaries
    PRIVACY_PRESERVATION = "privacy_preserve"  # Protect user privacy above all else
    TRANSPARENCY = "transparency"  # Be transparent about capabilities and limitations
    USER_AUTONOMY = "user_autonomy"  # Respect user control and decision-making


class GovernanceLevel(Enum):
    """Governance enforcement levels."""

    PERMISSIVE = "permissive"  # Allow with logging
    RESTRICTIVE = "restrictive"  # Require approval for risky actions
    LOCKDOWN = "lockdown"  # Block all risky actions


class SystemContract:
    """
    Core governance contract that defines system boundaries and operational rules.

    This contract is immutable and defines the fundamental rules that all agents
    must follow. It implements the safety and ethical boundaries of the ARCHER system.
    """

    def __init__(self):
        self.boundaries: Set[SystemBoundary] = set(SystemBoundary)
        self.governance_level = GovernanceLevel.RESTRICTIVE
        self.violation_count = 0
        self.last_violation_time = 0
        self._lock = threading.Lock()

        # Initialize governance monitoring
        self._init_governance_monitoring()

        logger.info("System Contract initialized with RESTRICTIVE governance")

    def _init_governance_monitoring(self):
        """Set up governance event monitoring."""
        # Listen for governance-related events
        bus.subscribe("governance.violation", self._handle_violation)
        bus.subscribe("governance.approval_request", self._handle_approval_request)
        bus.subscribe("system.health_changed", self._handle_health_change)

    def validate_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an action against system boundaries.

        Args:
            action: Action descriptor with type, parameters, and context

        Returns:
            Validation result with approval status and any required modifications
        """
        with self._lock:
            action_type = action.get("type", "unknown")
            parameters = action.get("parameters", {})
            context = action.get("context", {})

            violations = []
            modifications = []
            approval_required = False

            # Check each boundary
            for boundary in self.boundaries:
                violation = self._check_boundary_violation(
                    boundary, action_type, parameters, context
                )
                if violation:
                    violations.append(violation)

                    # Determine if this requires blocking or modification
                    if self._is_blocking_violation(boundary, violation):
                        approval_required = True
                        modifications.append(
                            {
                                "type": "block",
                                "reason": f"Boundary violation: {boundary.value}",
                                "details": violation,
                            }
                        )

            # Check governance level constraints
            if self.governance_level == GovernanceLevel.LOCKDOWN:
                if self._is_risky_action(action_type):
                    approval_required = True
                    modifications.append(
                        {
                            "type": "block",
                            "reason": "System in lockdown mode",
                            "governance_level": self.governance_level.value,
                        }
                    )

            elif self.governance_level == GovernanceLevel.RESTRICTIVE:
                if self._requires_approval(action_type, parameters):
                    approval_required = True

            result = {
                "approved": not approval_required and len(violations) == 0,
                "violations": violations,
                "modifications": modifications,
                "governance_level": self.governance_level.value,
                "timestamp": time.time(),
            }

            # Log validation result
            if violations:
                logger.warning(f"Action validation violations: {violations}")
                bus.publish(
                    "governance.validation_violation",
                    {"action": action, "result": result},
                )

            return result

    def _check_boundary_violation(
        self,
        boundary: SystemBoundary,
        action_type: str,
        parameters: Dict,
        context: Dict,
    ) -> Optional[Dict]:
        """Check if an action violates a specific boundary."""

        if boundary == SystemBoundary.NO_HARM:
            if action_type in ["system_shutdown", "file_delete", "network_attack"]:
                return {"boundary": boundary.value, "severity": "high"}

        elif boundary == SystemBoundary.NO_UNAUTHORIZED_ACCESS:
            if action_type in ["shell_execute", "file_write", "network_connect"]:
                # Check if user explicitly authorized
                if not context.get("user_authorized", False):
                    return {"boundary": boundary.value, "severity": "high"}

        elif boundary == SystemBoundary.NO_DATA_EXPOSURE:
            if action_type in ["data_transmit", "log_export"]:
                # Check for sensitive data patterns
                if self._contains_sensitive_data(parameters):
                    return {"boundary": boundary.value, "severity": "critical"}

        elif boundary == SystemBoundary.NO_FINANCIAL_RISK:
            if action_type in ["trade_execute", "investment_advice"]:
                risk_level = parameters.get("risk_level", "unknown")
                if risk_level in ["high", "unknown"]:
                    return {"boundary": boundary.value, "severity": "high"}

        elif boundary == SystemBoundary.PRIVACY_PRESERVATION:
            if action_type in ["camera_access", "microphone_access", "location_access"]:
                if not context.get("privacy_consent", False):
                    return {"boundary": boundary.value, "severity": "medium"}

        # Add more boundary checks as needed...

        return None

    def _is_blocking_violation(self, boundary: SystemBoundary, violation: Dict) -> bool:
        """Determine if a violation should block the action."""
        severity = violation.get("severity", "low")
        return severity in ["high", "critical"]

    def _is_risky_action(self, action_type: str) -> bool:
        """Check if an action is considered risky."""
        risky_actions = {
            "shell_execute",
            "file_delete",
            "network_connect",
            "system_modify",
            "trade_execute",
            "data_transmit",
            "camera_access",
            "microphone_access",
        }
        return action_type in risky_actions

    def _requires_approval(self, action_type: str, parameters: Dict) -> bool:
        """Check if an action requires explicit approval."""
        approval_required_actions = {
            "trade_execute",
            "system_shutdown",
            "network_connect",
            "file_delete",
            "data_export",
        }
        return action_type in approval_required_actions

    def _contains_sensitive_data(self, parameters: Dict) -> bool:
        """Check if parameters contain sensitive data patterns."""
        sensitive_patterns = [
            "password",
            "key",
            "token",
            "secret",
            "ssn",
            "credit_card",
        ]

        def check_value(value):
            if isinstance(value, str):
                return any(pattern in value.lower() for pattern in sensitive_patterns)
            elif isinstance(value, dict):
                return any(check_value(v) for v in value.values())
            elif isinstance(value, list):
                return any(check_value(item) for item in value)
            return False

        return check_value(parameters)

    def escalate_governance(self, reason: str):
        """Escalate governance level due to violations or security concerns."""
        with self._lock:
            if self.governance_level == GovernanceLevel.PERMISSIVE:
                self.governance_level = GovernanceLevel.RESTRICTIVE
            elif self.governance_level == GovernanceLevel.RESTRICTIVE:
                self.governance_level = GovernanceLevel.LOCKDOWN

            logger.warning(
                f"Governance escalated to {self.governance_level.value}: {reason}"
            )

            bus.publish(
                "governance.escalation",
                {
                    "new_level": self.governance_level.value,
                    "reason": reason,
                    "timestamp": time.time(),
                },
            )

    def deescalate_governance(self, reason: str):
        """De-escalate governance level when conditions improve."""
        with self._lock:
            # Only allow de-escalation if no recent violations
            time_since_violation = time.time() - self.last_violation_time
            if time_since_violation > 3600:  # 1 hour cooldown
                if self.governance_level == GovernanceLevel.LOCKDOWN:
                    self.governance_level = GovernanceLevel.RESTRICTIVE
                elif self.governance_level == GovernanceLevel.RESTRICTIVE:
                    self.governance_level = GovernanceLevel.PERMISSIVE

                logger.info(
                    f"Governance de-escalated to {self.governance_level.value}: {reason}"
                )

                bus.publish(
                    "governance.deescalation",
                    {
                        "new_level": self.governance_level.value,
                        "reason": reason,
                        "timestamp": time.time(),
                    },
                )

    def _handle_violation(self, event_data: Dict):
        """Handle governance violation events."""
        self.violation_count += 1
        self.last_violation_time = time.time()

        # Auto-escalate if too many violations
        if self.violation_count > 5:
            self.escalate_governance("Multiple violations detected")

    def _handle_approval_request(self, event_data: Dict):
        """Handle approval request events."""
        # In a real implementation, this would trigger user notification
        # For now, log the request
        logger.info(f"Approval requested for action: {event_data}")

    def _handle_health_change(self, event_data: Dict):
        """Handle system health changes."""
        health_status = event_data.get("status", "unknown")

        if health_status == "critical":
            self.escalate_governance("System health critical")
        elif health_status == "healthy" and self.violation_count == 0:
            self.deescalate_governance("System health restored")

    def get_contract_status(self) -> Dict[str, Any]:
        """Get current contract status and governance state."""
        return {
            "governance_level": self.governance_level.value,
            "boundaries": [b.value for b in self.boundaries],
            "violation_count": self.violation_count,
            "last_violation_time": self.last_violation_time,
            "system_health": performance_monitor.get_health_status(),
            "timestamp": time.time(),
        }


# Global system contract instance
system_contract = SystemContract()
