"""
ARCHER Agent Supervisor - Execution Budgets & Resource Management

Manages agent execution budgets, resource allocation, and prevents
system overload through intelligent scheduling and throttling.
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict
import statistics

from src.events.bus import bus
from src.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


class ExecutionBudget:
    """Represents an execution budget for an agent or operation."""

    def __init__(
        self,
        name: str,
        max_concurrent: int = 1,
        max_per_hour: int = 60,
        max_per_day: int = 1000,
        cpu_budget: float = 50.0,
        memory_budget_mb: float = 500,
    ):
        self.name = name
        self.max_concurrent = max_concurrent
        self.max_per_hour = max_per_hour
        self.max_per_day = max_per_day
        self.cpu_budget = cpu_budget  # Max CPU % usage
        self.memory_budget_mb = memory_budget_mb

        # Tracking
        self.active_executions = 0
        self.hourly_count = 0
        self.daily_count = 0
        self.last_hour_reset = time.time()
        self.last_day_reset = time.time()
        self.cpu_usage = 0.0
        self.memory_usage_mb = 0.0

    def can_execute(self) -> Tuple[bool, str]:
        """Check if execution is allowed under current budget."""
        current_time = time.time()

        # Reset counters if needed
        if current_time - self.last_hour_reset > 3600:
            self.hourly_count = 0
            self.last_hour_reset = current_time

        if current_time - self.last_day_reset > 86400:
            self.daily_count = 0
            self.last_day_reset = current_time

        # Check limits
        if self.active_executions >= self.max_concurrent:
            return False, f"Max concurrent executions ({self.max_concurrent}) reached"

        if self.hourly_count >= self.max_per_hour:
            return False, f"Hourly limit ({self.max_per_hour}) reached"

        if self.daily_count >= self.max_per_day:
            return False, f"Daily limit ({self.max_per_day}) reached"

        # Check resource budgets
        health_status = performance_monitor.get_health_status()
        if health_status["cpu"] == "healthy" and self.cpu_usage > self.cpu_budget:
            return False, f"CPU budget ({self.cpu_budget}%) exceeded"

        return True, "OK"

    def start_execution(self) -> bool:
        """Start a new execution under this budget."""
        can_execute, reason = self.can_execute()
        if can_execute:
            self.active_executions += 1
            self.hourly_count += 1
            self.daily_count += 1
            return True
        return False

    def end_execution(self):
        """End an active execution."""
        if self.active_executions > 0:
            self.active_executions -= 1

    def update_resource_usage(self, cpu_percent: float, memory_mb: float):
        """Update resource usage tracking."""
        self.cpu_usage = cpu_percent
        self.memory_usage_mb = memory_mb


class AgentSupervisor:
    """
    Supervises agent execution with budgets and resource management.

    Prevents system overload by managing execution budgets, prioritizing
    critical operations, and throttling non-essential activities.
    """

    def __init__(self):
        self.budgets: Dict[str, ExecutionBudget] = {}
        self.active_operations: Dict[str, Dict] = {}
        self.operation_queue: List[Dict] = []
        self._lock = threading.Lock()

        # Default budgets for different agent types
        self._init_default_budgets()

        # Initialize supervision
        self._init_supervision()

        logger.info("Agent Supervisor initialized")

    def _init_default_budgets(self):
        """Initialize default execution budgets."""
        # Core system agents - high priority
        self.budgets["voice_pipeline"] = ExecutionBudget(
            "voice_pipeline", max_concurrent=1, max_per_hour=120, cpu_budget=80.0
        )
        self.budgets["observer"] = ExecutionBudget(
            "observer", max_concurrent=1, max_per_hour=60, cpu_budget=60.0
        )

        # Specialist agents - medium priority
        self.budgets["assistant"] = ExecutionBudget(
            "assistant", max_concurrent=2, max_per_hour=100, cpu_budget=40.0
        )
        self.budgets["therapist"] = ExecutionBudget(
            "therapist", max_concurrent=1, max_per_hour=50, cpu_budget=30.0
        )
        self.budgets["trainer"] = ExecutionBudget(
            "trainer", max_concurrent=1, max_per_hour=30, cpu_budget=30.0
        )

        # Background agents - lower priority
        self.budgets["stock_expert"] = ExecutionBudget(
            "stock_expert", max_concurrent=1, max_per_hour=20, cpu_budget=20.0
        )
        self.budgets["rnd_agent"] = ExecutionBudget(
            "rnd_agent", max_concurrent=1, max_per_hour=10, cpu_budget=15.0
        )

    def _init_supervision(self):
        """Set up supervision event handlers."""
        bus.subscribe("performance.alert", self._handle_performance_alert)
        bus.subscribe("system.health_changed", self._handle_health_change)
        bus.subscribe("supervisor.execute_request", self._handle_execution_request)

    def request_execution(
        self,
        agent_name: str,
        operation: str,
        priority: str = "normal",
        context: Dict = None,
    ) -> Dict[str, Any]:
        """
        Request execution permission for an agent operation.

        Returns execution approval with details.
        """
        with self._lock:
            budget = self.budgets.get(agent_name)
            if not budget:
                # Create default budget for unknown agents
                budget = ExecutionBudget(agent_name, max_concurrent=1, max_per_hour=10)
                self.budgets[agent_name] = budget

            can_execute, reason = budget.can_execute()

            # Check system health for high-priority operations
            health_status = performance_monitor.get_health_status()
            if priority == "high" and health_status["overall"] != "healthy":
                can_execute = False
                reason = f"System health {health_status['overall']} prevents high-priority execution"

            result = {
                "approved": can_execute,
                "reason": reason,
                "agent": agent_name,
                "operation": operation,
                "priority": priority,
                "queue_position": 0,
                "estimated_delay": 0,
                "timestamp": time.time(),
            }

            if can_execute:
                # Start execution tracking
                execution_id = f"{agent_name}_{operation}_{int(time.time())}"
                budget.start_execution()

                self.active_operations[execution_id] = {
                    "agent": agent_name,
                    "operation": operation,
                    "start_time": time.time(),
                    "priority": priority,
                    "context": context,
                }

                result["execution_id"] = execution_id

                bus.publish(
                    "supervisor.execution_started",
                    {
                        "execution_id": execution_id,
                        "agent": agent_name,
                        "operation": operation,
                        "priority": priority,
                    },
                )

            else:
                # Queue the operation if appropriate
                if self._should_queue_operation(agent_name, operation, priority):
                    queue_item = {
                        "agent": agent_name,
                        "operation": operation,
                        "priority": priority,
                        "context": context,
                        "queued_at": time.time(),
                    }
                    self.operation_queue.append(queue_item)
                    result["queued"] = True
                    result["queue_position"] = len(self.operation_queue)

                    bus.publish("supervisor.execution_queued", queue_item)

            return result

    def complete_execution(
        self, execution_id: str, success: bool = True, metrics: Dict = None
    ):
        """Mark an execution as completed."""
        with self._lock:
            if execution_id in self.active_operations:
                operation = self.active_operations.pop(execution_id)
                agent_name = operation["agent"]

                # Update budget
                if agent_name in self.budgets:
                    self.budgets[agent_name].end_execution()

                # Record metrics
                duration = time.time() - operation["start_time"]
                if metrics:
                    performance_monitor.record_metric(
                        f"execution_duration_{agent_name}",
                        duration * 1000,  # Convert to ms
                        "ms",
                    )

                bus.publish(
                    "supervisor.execution_completed",
                    {
                        "execution_id": execution_id,
                        "agent": agent_name,
                        "operation": operation["operation"],
                        "duration": duration,
                        "success": success,
                        "metrics": metrics,
                    },
                )

                # Process queued operations
                self._process_operation_queue()

    def _should_queue_operation(
        self, agent_name: str, operation: str, priority: str
    ) -> bool:
        """Determine if an operation should be queued."""
        # High priority operations should not be queued
        if priority == "high":
            return False

        # Core operations should not be queued
        core_operations = ["voice_pipeline", "observer"]
        if agent_name in core_operations:
            return False

        return True

    def _process_operation_queue(self):
        """Process queued operations that can now execute."""
        # Sort queue by priority
        priority_order = {"high": 0, "normal": 1, "low": 2}
        self.operation_queue.sort(key=lambda x: priority_order.get(x["priority"], 1))

        # Try to execute operations that can now run
        remaining_queue = []
        for queued_op in self.operation_queue:
            result = self.request_execution(
                queued_op["agent"],
                queued_op["operation"],
                queued_op["priority"],
                queued_op["context"],
            )

            if not result["approved"]:
                remaining_queue.append(queued_op)
            # If approved, it's now executing

        self.operation_queue = remaining_queue

    def throttle_agent(self, agent_name: str, duration_seconds: float, reason: str):
        """Temporarily throttle an agent."""
        with self._lock:
            if agent_name in self.budgets:
                budget = self.budgets[agent_name]
                # Temporarily reduce limits
                budget.max_concurrent = max(1, budget.max_concurrent // 2)
                budget.max_per_hour = max(5, budget.max_per_hour // 2)

                # Schedule restoration
                def restore_limits():
                    time.sleep(duration_seconds)
                    with self._lock:
                        # Restore original limits (this is simplified)
                        budget.max_concurrent = min(5, budget.max_concurrent * 2)
                        budget.max_per_hour = min(100, budget.max_per_hour * 2)

                threading.Thread(target=restore_limits, daemon=True).start()

                logger.info(
                    f"Throttled agent {agent_name} for {duration_seconds}s: {reason}"
                )

                bus.publish(
                    "supervisor.agent_throttled",
                    {
                        "agent": agent_name,
                        "duration": duration_seconds,
                        "reason": reason,
                    },
                )

    def get_supervisor_status(self) -> Dict[str, Any]:
        """Get comprehensive supervisor status."""
        with self._lock:
            budget_status = {}
            for name, budget in self.budgets.items():
                budget_status[name] = {
                    "active_executions": budget.active_executions,
                    "hourly_count": budget.hourly_count,
                    "daily_count": budget.daily_count,
                    "cpu_usage": budget.cpu_usage,
                    "memory_usage_mb": budget.memory_usage_mb,
                }

            return {
                "active_operations": len(self.active_operations),
                "queued_operations": len(self.operation_queue),
                "budgets": budget_status,
                "system_health": performance_monitor.get_health_status(),
                "timestamp": time.time(),
            }

    def _handle_performance_alert(self, event_data: Dict):
        """Handle performance alerts by throttling if needed."""
        severity = event_data.get("severity", "warning")
        metric = event_data.get("metric", "unknown")

        if severity == "critical":
            # Throttle non-essential agents
            for agent_name in ["stock_expert", "rnd_agent"]:
                self.throttle_agent(agent_name, 300, f"Critical performance: {metric}")

    def _handle_health_change(self, event_data: Dict):
        """Handle system health changes."""
        status = event_data.get("status", "unknown")

        if status == "critical":
            # Aggressive throttling
            for agent_name in self.budgets.keys():
                if agent_name not in ["voice_pipeline", "observer"]:
                    self.throttle_agent(agent_name, 600, "System health critical")

    def _handle_execution_request(self, event_data: Dict):
        """Handle execution requests from agents."""
        agent_name = event_data.get("agent", "unknown")
        operation = event_data.get("operation", "unknown")
        priority = event_data.get("priority", "normal")
        context = event_data.get("context", {})

        result = self.request_execution(agent_name, operation, priority, context)

        # Publish result
        bus.publish("supervisor.execution_result", result)


# Global supervisor instance
agent_supervisor = AgentSupervisor()
