"""
ARCHER Evidence Processor - Confidence Accumulation Model

Processes and accumulates evidence from multiple sources to build
confidence in observations and decisions.
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import statistics

from src.events.bus import bus
from src.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


class Evidence:
    """Represents a piece of evidence with confidence and metadata."""

    def __init__(
        self,
        source: str,
        evidence_type: str,
        value: Any,
        confidence: float,
        timestamp: float = None,
        metadata: Dict = None,
    ):
        self.source = source
        self.evidence_type = evidence_type
        self.value = value
        self.confidence = confidence
        self.timestamp = timestamp or time.time()
        self.metadata = metadata or {}

    def is_recent(self, max_age_seconds: float = 300) -> bool:
        """Check if evidence is recent."""
        return (time.time() - self.timestamp) < max_age_seconds

    def get_weighted_confidence(self) -> float:
        """Get confidence weighted by recency."""
        age_hours = (time.time() - self.timestamp) / 3600
        recency_weight = max(0.1, 1.0 - (age_hours / 24))  # Decay over 24 hours
        return self.confidence * recency_weight


class EvidenceProcessor:
    """
    Processes and accumulates evidence from multiple sources.

    Builds confidence in observations and decisions through evidence accumulation,
    conflict resolution, and consensus building.
    """

    def __init__(
        self, min_evidence_threshold: int = 3, confidence_threshold: float = 0.7
    ):
        self.evidence_store: Dict[str, List[Evidence]] = defaultdict(list)
        self.consensus_cache: Dict[str, Dict] = {}
        self.min_evidence_threshold = min_evidence_threshold
        self.confidence_threshold = confidence_threshold
        self._lock = threading.Lock()

        # Initialize evidence processing
        self._init_evidence_processing()

        logger.info("Evidence Processor initialized")

    def _init_evidence_processing(self):
        """Set up evidence processing event handlers."""
        bus.subscribe("vision.observation.emotion", self._handle_vision_evidence)
        bus.subscribe("vision.observation.posture", self._handle_vision_evidence)
        bus.subscribe("performance.metric_recorded", self._handle_performance_evidence)
        bus.subscribe("authority.action_recorded", self._handle_authority_evidence)

    def add_evidence(
        self,
        source: str,
        evidence_type: str,
        value: Any,
        confidence: float,
        metadata: Dict = None,
    ) -> str:
        """
        Add new evidence to the processor.

        Returns evidence ID.
        """
        with self._lock:
            evidence_id = f"{evidence_type}_{source}_{int(time.time())}"

            evidence = Evidence(
                source=source,
                evidence_type=evidence_type,
                value=value,
                confidence=confidence,
                metadata=metadata,
            )

            self.evidence_store[evidence_type].append(evidence)

            # Clean old evidence (keep last 100 per type)
            if len(self.evidence_store[evidence_type]) > 100:
                self.evidence_store[evidence_type] = self.evidence_store[evidence_type][
                    -100:
                ]

            # Invalidate consensus cache for this type
            if evidence_type in self.consensus_cache:
                del self.consensus_cache[evidence_type]

            logger.debug(
                f"Evidence added: {evidence_type} from {source} (confidence: {confidence})"
            )

            return evidence_id

    def get_consensus(
        self, evidence_type: str, min_samples: int = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get consensus for an evidence type.

        Returns consensus information or None if insufficient evidence.
        """
        min_samples = min_samples or self.min_evidence_threshold

        with self._lock:
            # Check cache first
            if evidence_type in self.consensus_cache:
                cached = self.consensus_cache[evidence_type]
                if time.time() - cached["timestamp"] < 60:  # Cache for 1 minute
                    return cached

            evidences = self.evidence_store.get(evidence_type, [])

            # Filter recent evidence
            recent_evidences = [e for e in evidences if e.is_recent()]

            if len(recent_evidences) < min_samples:
                return None

            # Calculate consensus
            consensus = self._calculate_consensus(evidence_type, recent_evidences)

            # Cache result
            consensus["timestamp"] = time.time()
            self.consensus_cache[evidence_type] = consensus

            return consensus

    def _calculate_consensus(
        self, evidence_type: str, evidences: List[Evidence]
    ) -> Dict[str, Any]:
        """Calculate consensus from multiple evidence sources."""

        if not evidences:
            return {"consensus_value": None, "confidence": 0.0, "sample_count": 0}

        # Group by value for categorical consensus
        value_weights = defaultdict(float)
        total_weight = 0

        for evidence in evidences:
            weight = evidence.get_weighted_confidence()
            value_weights[evidence.value] += weight
            total_weight += weight

        if total_weight == 0:
            return {
                "consensus_value": None,
                "confidence": 0.0,
                "sample_count": len(evidences),
            }

        # Find consensus value (highest weighted)
        consensus_value = max(value_weights.items(), key=lambda x: x[1])[0]

        # Calculate consensus confidence
        consensus_weight = value_weights[consensus_value]
        consensus_confidence = consensus_weight / total_weight

        # Calculate agreement level (how dominant the consensus is)
        sorted_weights = sorted(value_weights.values(), reverse=True)
        if len(sorted_weights) > 1:
            agreement_ratio = sorted_weights[0] / sum(sorted_weights[1:])
        else:
            agreement_ratio = float("inf")

        return {
            "consensus_value": consensus_value,
            "confidence": consensus_confidence,
            "agreement_ratio": agreement_ratio,
            "sample_count": len(evidences),
            "sources": list(set(e.source for e in evidences)),
            "value_distribution": dict(value_weights),
        }

    def check_confidence_threshold(self, evidence_type: str) -> Tuple[bool, float]:
        """
        Check if evidence type meets confidence threshold.

        Returns (meets_threshold, confidence_level).
        """
        consensus = self.get_consensus(evidence_type)
        if not consensus:
            return False, 0.0

        confidence = consensus.get("confidence", 0.0)
        meets_threshold = confidence >= self.confidence_threshold

        return meets_threshold, confidence

    def get_evidence_summary(self) -> Dict[str, Any]:
        """Get summary of all evidence types."""
        with self._lock:
            summary = {}
            for evidence_type, evidences in self.evidence_store.items():
                recent_evidences = [e for e in evidences if e.is_recent()]
                consensus = self.get_consensus(evidence_type, min_samples=1)

                summary[evidence_type] = {
                    "total_samples": len(evidences),
                    "recent_samples": len(recent_evidences),
                    "has_consensus": consensus is not None,
                    "consensus_confidence": consensus.get("confidence", 0.0)
                    if consensus
                    else 0.0,
                    "sources": list(set(e.source for e in recent_evidences)),
                }

            return summary

    def _handle_vision_evidence(self, event_data: Dict):
        """Handle vision observation evidence."""
        emotion = event_data.get("emotion")
        confidence = event_data.get("confidence", 0.0)

        if emotion:
            self.add_evidence(
                source="vision_observer",
                evidence_type="user_emotion",
                value=emotion,
                confidence=confidence,
                metadata={"posture": event_data.get("posture")},
            )

    def _handle_performance_evidence(self, event_data: Dict):
        """Handle performance metric evidence."""
        metric = event_data.get("metric")
        value = event_data.get("value", 0.0)

        if metric and value > 0:
            # Convert performance metrics to confidence indicators
            confidence = min(
                1.0, max(0.0, 1.0 - (value / 1000))
            )  # Lower values = higher confidence

            self.add_evidence(
                source="performance_monitor",
                evidence_type=f"performance_{metric}",
                value=value,
                confidence=confidence,
                metadata={"unit": event_data.get("unit", "unknown")},
            )

    def _handle_authority_evidence(self, event_data: Dict):
        """Handle authority action evidence."""
        success = event_data.get("success", False)
        confidence = event_data.get("new_confidence", 0.5)

        self.add_evidence(
            source="authority_manager",
            evidence_type="authority_effectiveness",
            value=success,
            confidence=confidence,
            metadata={"action_type": event_data.get("action_type")},
        )

    def clear_old_evidence(self, max_age_hours: float = 24):
        """Clear evidence older than specified age."""
        with self._lock:
            cutoff_time = time.time() - (max_age_hours * 3600)

            for evidence_type in self.evidence_store:
                self.evidence_store[evidence_type] = [
                    e
                    for e in self.evidence_store[evidence_type]
                    if e.timestamp > cutoff_time
                ]

            logger.info(f"Cleared evidence older than {max_age_hours} hours")


# Global evidence processor instance
evidence_processor = EvidenceProcessor()
