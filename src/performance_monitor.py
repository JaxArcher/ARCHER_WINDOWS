"""
ARCHER Performance Monitor - Latency Instrumentation & Metrics

Provides comprehensive performance monitoring for production readiness.
Tracks latency, throughput, and system health metrics.
"""

import time
import threading
import logging
import statistics
from collections import deque
from typing import Dict, List, Optional, Any
import os

from src.events.bus import bus
from src.platform_utils import get_gpu_info

logger = logging.getLogger(__name__)

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available, system monitoring disabled")


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system for ARCHER.

    Tracks latency metrics, system resources, and performance health.
    Provides real-time monitoring and alerting capabilities.
    """

    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._lock = threading.Lock()

        # Latency tracking (rolling windows)
        self.latency_metrics = {
            "voice_pipeline_total": deque(maxlen=max_samples),
            "stt_latency": deque(maxlen=max_samples),
            "llm_latency": deque(maxlen=max_samples),
            "tts_latency": deque(maxlen=max_samples),
            "wake_word_detection": deque(maxlen=max_samples),
            "emotion_analysis": deque(maxlen=max_samples),
            "observer_processing": deque(maxlen=max_samples),
        }

        # Throughput tracking
        self.throughput_metrics = {
            "voice_interactions_per_minute": deque(maxlen=60),  # 1 hour rolling
            "observer_frames_per_second": deque(maxlen=60),
            "memory_usage_mb": deque(maxlen=60),
            "cpu_usage_percent": deque(maxlen=60),
        }

        # Performance thresholds (ms)
        self.thresholds = {
            "voice_pipeline_total": 1000,  # < 1s target
            "stt_latency": 500,
            "llm_latency": 2000,
            "tts_latency": 300,
            "wake_word_detection": 100,
        }

        # Health status
        self.health_status = {
            "overall": "healthy",
            "voice_pipeline": "healthy",
            "observer": "healthy",
            "memory": "healthy",
            "cpu": "healthy",
        }

        # Active timers
        self.active_timers: Dict[str, float] = {}

        # System monitoring
        self.system_monitor_thread = threading.Thread(
            target=self._monitor_system_resources, daemon=True
        )
        self.system_monitor_thread.start()

        logger.info("Performance Monitor initialized")

    def start_timer(self, metric_name: str) -> str:
        """Start timing a performance metric."""
        timer_id = f"{metric_name}_{time.time()}"
        self.active_timers[timer_id] = time.time()
        return timer_id

    def end_timer(self, timer_id: str, metric_name: str) -> float:
        """End timing and record the metric."""
        if timer_id not in self.active_timers:
            logger.warning(f"Timer {timer_id} not found")
            return 0.0

        start_time = self.active_timers.pop(timer_id)
        duration = (time.time() - start_time) * 1000  # Convert to milliseconds

        with self._lock:
            if metric_name in self.latency_metrics:
                self.latency_metrics[metric_name].append(duration)

        # Publish performance event
        bus.publish(
            "performance.metric_recorded",
            {"metric": metric_name, "duration_ms": duration, "timestamp": time.time()},
        )

        # Check thresholds and alert if needed
        self._check_thresholds(metric_name, duration)

        return duration

    def record_metric(self, metric_name: str, value: float, unit: str = "ms"):
        """Record a performance metric value directly."""
        with self._lock:
            if metric_name in self.latency_metrics:
                self.latency_metrics[metric_name].append(value)
            elif metric_name in self.throughput_metrics:
                self.throughput_metrics[metric_name].append(value)

        # Publish performance event
        bus.publish(
            "performance.metric_recorded",
            {
                "metric": metric_name,
                "value": value,
                "unit": unit,
                "timestamp": time.time(),
            },
        )

    def get_metric_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistical summary for a metric."""
        with self._lock:
            if metric_name in self.latency_metrics:
                values = list(self.latency_metrics[metric_name])
            elif metric_name in self.throughput_metrics:
                values = list(self.throughput_metrics[metric_name])
            else:
                return {}

            if not values:
                return {}

            return {
                "count": len(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "min": min(values),
                "max": max(values),
                "p95": statistics.quantiles(values, n=20)[18]
                if len(values) >= 20
                else max(values),
                "p99": statistics.quantiles(values, n=100)[98]
                if len(values) >= 100
                else max(values),
            }

    def get_health_status(self) -> Dict[str, str]:
        """Get current health status of all components."""
        return self.health_status.copy()

    def _check_thresholds(self, metric_name: str, value: float):
        """Check if metric exceeds performance thresholds."""
        if metric_name in self.thresholds:
            threshold = self.thresholds[metric_name]
            if value > threshold:
                self._alert_performance_issue(metric_name, value, threshold)

    def _alert_performance_issue(
        self, metric_name: str, value: float, threshold: float
    ):
        """Alert on performance threshold violations."""
        severity = "warning" if value < threshold * 1.5 else "critical"

        # Update health status
        component = metric_name.split("_")[0]  # Extract component name
        if component in self.health_status:
            self.health_status[component] = (
                "degraded" if severity == "warning" else "critical"
            )

        # Update overall health
        if any(status != "healthy" for status in self.health_status.values()):
            self.health_status["overall"] = "degraded"
        if any(status == "critical" for status in self.health_status.values()):
            self.health_status["overall"] = "critical"

        bus.publish(
            "performance.alert",
            {
                "metric": metric_name,
                "value": value,
                "threshold": threshold,
                "severity": severity,
                "timestamp": time.time(),
            },
        )

        logger.warning(
            f"PERFORMANCE ALERT: {metric_name} = {value:.1f}ms (threshold: {threshold}ms)"
        )

    def _monitor_system_resources(self):
        """Monitor system resources in background."""
        if not PSUTIL_AVAILABLE:
            logger.info("System resource monitoring disabled (psutil not available)")
            return

        while True:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.record_metric("cpu_usage_percent", cpu_percent, "percent")

                # Memory usage
                memory = psutil.virtual_memory()
                memory_mb = memory.used / (1024 * 1024)
                self.record_metric("memory_usage_mb", memory_mb, "MB")

                # Memory health check
                if memory.percent > 90:
                    self.health_status["memory"] = "critical"
                elif memory.percent > 80:
                    self.health_status["memory"] = "degraded"
                else:
                    self.health_status["memory"] = "healthy"

                # CPU health check
                if cpu_percent > 95:
                    self.health_status["cpu"] = "critical"
                elif cpu_percent > 85:
                    self.health_status["cpu"] = "degraded"
                else:
                    self.health_status["cpu"] = "healthy"

                # GPU monitoring
                gpu_info = get_gpu_info()
                if gpu_info["available"]:
                    # GPU memory usage
                    memory_used_mb = gpu_info["memory_used"] / (1024 * 1024)
                    self.record_metric("gpu_memory_used_mb", memory_used_mb, "MB")

                    memory_total_mb = gpu_info["memory_total"] / (1024 * 1024)
                    self.record_metric("gpu_memory_total_mb", memory_total_mb, "MB")

                    # GPU memory utilization
                    if gpu_info["memory_total"] > 0:
                        memory_percent = (
                            gpu_info["memory_used"] / gpu_info["memory_total"]
                        ) * 100
                        self.record_metric(
                            "gpu_memory_percent", memory_percent, "percent"
                        )

                        # GPU memory health check
                        if memory_percent > 95:
                            self.health_status["gpu_memory"] = "critical"
                        elif memory_percent > 85:
                            self.health_status["gpu_memory"] = "degraded"
                        else:
                            self.health_status["gpu_memory"] = "healthy"

                    # GPU name
                    if "name" in gpu_info:
                        self.record_metric("gpu_name", gpu_info["name"], "string")
                else:
                    self.health_status["gpu"] = "unavailable"

                # Update overall health
                self._update_overall_health()

                time.sleep(10)  # Monitor every 10 seconds

            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                time.sleep(30)

    def _update_overall_health(self):
        """Update overall system health based on component health."""
        statuses = [
            status for key, status in self.health_status.items() if key != "overall"
        ]

        if "critical" in statuses:
            self.health_status["overall"] = "critical"
        elif "degraded" in statuses:
            self.health_status["overall"] = "degraded"
        else:
            self.health_status["overall"] = "healthy"

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {
            "timestamp": time.time(),
            "health_status": self.get_health_status(),
            "metrics": {},
        }

        # Collect stats for all metrics
        all_metrics = list(self.latency_metrics.keys()) + list(
            self.throughput_metrics.keys()
        )
        for metric in all_metrics:
            stats = self.get_metric_stats(metric)
            if stats:
                report["metrics"][metric] = stats

        return report

    def log_benchmark_results(self, results: Dict[str, Any]):
        """Log benchmark results to file and console."""
        import json
        import os

        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "performance_benchmarks.log")

        timestamp = time.time()
        log_entry = {"timestamp": timestamp, "results": results}

        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        logger.info("Benchmark results logged:")
        for component, latency in results.items():
            logger.info(f"  {component}: {latency:.1f}ms")

        # Record in performance monitor
        for component, latency in results.items():
            metric_name = f"{component}_latency"
            self.record_metric(metric_name, latency)


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
