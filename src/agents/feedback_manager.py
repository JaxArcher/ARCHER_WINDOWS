"""
RLHF Feedback Collection and Management System for ARCHER

Collects and manages user feedback for Reinforcement Learning from Human Feedback.
"""

import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
import os

logger = logging.getLogger(__name__)

@dataclass
class UserFeedback:
    """User feedback on ARCHER responses."""
    
    feedback_id: str
    timestamp: float
    interaction_id: str
    user_input: str
    archer_response: str
    feedback_score: float  # -1 to 1 scale (-1 = very negative, 1 = very positive)
    feedback_text: str = ""
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "timestamp": self.timestamp,
            "interaction_id": self.interaction_id,
            "user_input": self.user_input,
            "archer_response": self.archer_response,
            "feedback_score": self.feedback_score,
            "feedback_text": self.feedback_text,
            "tags": self.tags or [],
            "metadata": self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserFeedback":
        return cls(
            feedback_id=data["feedback_id"],
            timestamp=data["timestamp"],
            interaction_id=data["interaction_id"],
            user_input=data["user_input"],
            archer_response=data["archer_response"],
            feedback_score=data["feedback_score"],
            feedback_text=data.get("feedback_text", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )

class FeedbackManager:
    """
    RLHF Feedback Collection and Management System.
    
    Features:
    - Collect explicit and implicit feedback
    - Store feedback with full context
    - Analyze feedback patterns and trends
    - Generate training data for RLHF
    - Manage feedback lifecycle
    """
    
    def __init__(self, storage_file: str = "data/user_feedback.json"):
        self.storage_file = storage_file
        self.feedback_store: List[UserFeedback] = self._load_feedback()
        self.current_interaction: Optional[Dict[str, Any]] = None
        self.feedback_enabled = True
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(storage_file), exist_ok=True)
        
        logger.info(f"FeedbackManager initialized with {len(self.feedback_store)} existing feedback entries")
    
    def _load_feedback(self) -> List[UserFeedback]:
        """Load feedback from storage."""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [UserFeedback.from_dict(item) for item in data]
        except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
            logger.warning(f"Could not load feedback: {e}")
        
        return []
    
    def _save_feedback(self) -> bool:
        """Save feedback to storage."""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump([fb.to_dict() for fb in self.feedback_store], f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save feedback: {e}")
            return False
    
    def enable_feedback_collection(self, enabled: bool = True):
        """Enable or disable feedback collection."""
        self.feedback_enabled = enabled
        logger.info(f"Feedback collection {'enabled' if enabled else 'disabled'}")
    
    def start_interaction(self, interaction_id: str, user_input: str, metadata: Dict[str, Any] = None):
        """Start tracking an interaction for feedback."""
        if not self.feedback_enabled:
            return
        
        self.current_interaction = {
            "interaction_id": interaction_id,
            "user_input": user_input,
            "start_time": time.time(),
            "response": None,
            "response_time": None,
            "metadata": metadata or {}
        }
        
        logger.debug(f"Started tracking interaction: {interaction_id}")
    
    def record_response(self, response: str):
        """Record ARCHER's response for feedback tracking."""
        if not self.feedback_enabled or not self.current_interaction:
            return
        
        self.current_interaction["response"] = response
        self.current_interaction["response_time"] = time.time()
        
        logger.debug(f"Recorded response for interaction: {self.current_interaction['interaction_id']}")
    
    def collect_explicit_feedback(self, score: float, text: str = "", tags: List[str] = None, 
                                  additional_metadata: Dict[str, Any] = None) -> Optional[UserFeedback]:
        """
        Collect explicit user feedback.
        
        Args:
            score: Feedback score (-1 to 1)
            text: Optional feedback text
            tags: Optional tags/categories
            additional_metadata: Additional metadata
            
        Returns:
            UserFeedback object if successful, None otherwise
        """
        if not self.feedback_enabled:
            logger.debug("Feedback collection disabled")
            return None
        
        if not self.current_interaction:
            logger.warning("No active interaction to collect feedback for")
            return None
        
        try:
            # Calculate response latency
            latency = (self.current_interaction["response_time"] - 
                      self.current_interaction["start_time"]) if self.current_interaction["response_time"] else 0
            
            # Create feedback
            feedback = UserFeedback(
                feedback_id=f"fb_{int(time.time() * 1000)}_{len(self.feedback_store)}",
                timestamp=time.time(),
                interaction_id=self.current_interaction["interaction_id"],
                user_input=self.current_interaction["user_input"],
                archer_response=self.current_interaction["response"],
                feedback_score=float(max(-1.0, min(1.0, score))),
                feedback_text=text,
                tags=tags or [],
                metadata={
                    "response_latency": latency,
                    "response_length": len(self.current_interaction["response"]),
                    "user_input_length": len(self.current_interaction["user_input"]),
                    **(additional_metadata or {})
                }
            )
            
            # Add to store
            self.feedback_store.append(feedback)
            
            # Save to disk
            if self._save_feedback():
                logger.info(f"Collected explicit feedback: {feedback.feedback_id} (score: {score:.2f})")
            else:
                logger.warning("Feedback saved to memory but not to disk")
            
            # Reset current interaction
            self.current_interaction = None
            
            return feedback
            
        except Exception as e:
            logger.error(f"Failed to collect explicit feedback: {e}")
            return None
    
    def collect_implicit_feedback(self, interaction_data: Dict[str, Any]) -> Optional[UserFeedback]:
        """
        Collect implicit feedback from user behavior.
        
        Args:
            interaction_data: Dictionary containing interaction details
            
        Returns:
            UserFeedback object if feedback was collected, None otherwise
        """
        if not self.feedback_enabled:
            return None
        
        try:
            # Analyze interaction for implicit signals
            score = self._analyze_implicit_score(interaction_data)
            
            if score is not None:
                # Create implicit feedback
                feedback = UserFeedback(
                    feedback_id=f"fb_{int(time.time() * 1000)}_{len(self.feedback_store)}",
                    timestamp=time.time(),
                    interaction_id=interaction_data.get("interaction_id", f"implicit_{int(time.time())}"),
                    user_input=interaction_data.get("user_input", ""),
                    archer_response=interaction_data.get("response", ""),
                    feedback_score=score,
                    feedback_text="Implicit feedback from user behavior analysis",
                    tags=["implicit", "behavioral"],
                    metadata={
                        "source": "implicit",
                        "confidence": abs(score) * 0.5,  # Lower confidence for implicit feedback
                        "analysis_method": "textual_patterns"
                    }
                )
                
                # Add to store
                self.feedback_store.append(feedback)
                
                # Save to disk
                if self._save_feedback():
                    logger.info(f"Collected implicit feedback: {feedback.feedback_id} (score: {score:.2f})")
                
                return feedback
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to collect implicit feedback: {e}")
            return None
    
    def _analyze_implicit_score(self, interaction_data: Dict[str, Any]) -> Optional[float]:
        """
        Analyze implicit feedback signals from interaction data.
        
        Args:
            interaction_data: Dictionary with interaction details
            
        Returns:
            Feedback score (-0.5 to 0.5) or None if no clear signal
        """
        try:
            # Check for positive signals in user follow-up
            positive_signals = [
                "thanks", "thank you", "great", "awesome", "perfect",
                "exactly", "correct", "right", "yes", "good job",
                "excellent", "wonderful", "fantastic", "amazing", "brilliant",
                "helpful", "useful", "appreciate", "love it", "perfect"
            ]
            
            # Check for negative signals in user follow-up
            negative_signals = [
                "no", "wrong", "incorrect", "bad", "terrible",
                "not helpful", "don't like", "hate", "stop", "cancel",
                "awful", "horrible", "useless", "worst", "fail",
                "mistake", "error", "problem", "issue", "broken"
            ]
            
            # Check for positive signals in ARCHER's response being confirmed
            confirmation_signals = [
                "yes", "correct", "right", "exactly", "that's right",
                "you're right", "agree", "confirm", "affirmative", "true"
            ]
            
            response_lower = interaction_data.get("response", "").lower()
            user_followup = interaction_data.get("user_followup", "").lower()
            
            # Count signals
            positive_count = sum(1 for signal in positive_signals if signal in user_followup)
            negative_count = sum(1 for signal in negative_signals if signal in user_followup)
            confirmation_count = sum(1 for signal in confirmation_signals if signal in user_followup)
            
            # Calculate score
            total_positive = positive_count + confirmation_count * 0.7  # Confirmations are slightly less strong
            
            if total_positive > negative_count:
                # Positive feedback
                base_score = min(0.5, total_positive * 0.08)  # Cap implicit positive at 0.5
                # Boost score if user follow-up is longer (more engaged)
                followup_length = len(user_followup.split())
                if followup_length > 3:
                    base_score = min(0.5, base_score * 1.2)
                return base_score
            elif negative_count > total_positive:
                # Negative feedback
                base_score = max(-0.5, -negative_count * 0.1)  # Cap implicit negative at -0.5
                # More severe penalty for longer negative follow-ups
                followup_length = len(user_followup.split())
                if followup_length > 2:
                    base_score = max(-0.5, base_score * 1.3)
                return base_score
            
            return None
            
        except Exception as e:
            logger.error(f"Implicit feedback analysis failed: {e}")
            return None
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get comprehensive feedback statistics."""
        if not self.feedback_store:
            return {
                "count": 0,
                "average_score": 0.0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "explicit": 0,
                "implicit": 0
            }
        
        try:
            scores = [fb.feedback_score for fb in self.feedback_store]
            
            # Categorize feedback
            positive = sum(1 for s in scores if s > 0.3)
            negative = sum(1 for s in scores if s < -0.3)
            neutral = len(self.feedback_store) - positive - negative
            
            # Count by type
            explicit = sum(1 for fb in self.feedback_store if "implicit" not in fb.tags)
            implicit = len(self.feedback_store) - explicit
            
            # Calculate averages
            avg_score = sum(scores) / len(scores) if scores else 0.0
            avg_positive = sum(s for s in scores if s > 0) / max(1, positive) if positive else 0.0
            avg_negative = sum(s for s in scores if s < 0) / max(1, negative) if negative else 0.0
            
            return {
                "count": len(self.feedback_store),
                "average_score": round(avg_score, 3),
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "explicit": explicit,
                "implicit": implicit,
                "average_positive_score": round(avg_positive, 3),
                "average_negative_score": round(avg_negative, 3),
                "positive_percentage": round(positive / len(self.feedback_store) * 100, 1),
                "negative_percentage": round(negative / len(self.feedback_store) * 100, 1)
            }
        except Exception as e:
            logger.error(f"Failed to calculate feedback stats: {e}")
            return {"error": str(e)}
    
    def get_recent_feedback(self, limit: int = 10) -> List[UserFeedback]:
        """Get recent feedback entries."""
        return self.feedback_store[-limit:]
    
    def get_feedback_by_interaction(self, interaction_id: str) -> List[UserFeedback]:
        """Get feedback for a specific interaction."""
        return [fb for fb in self.feedback_store if fb.interaction_id == interaction_id]
    
    def get_feedback_by_time_range(self, start_time: float, end_time: float) -> List[UserFeedback]:
        """Get feedback within a time range."""
        return [fb for fb in self.feedback_store if start_time <= fb.timestamp <= end_time]
    
    def generate_rlhf_dataset(self, min_score: float = -0.7, max_samples: int = 1000, 
                            include_implicit: bool = True) -> List[Dict[str, Any]]:
        """
        Generate RLHF training dataset.
        
        Args:
            min_score: Minimum feedback score to include
            max_samples: Maximum number of samples
            include_implicit: Whether to include implicit feedback
            
        Returns:
            List of training examples in RLHF format
        """
        try:
            # Filter feedback
            filtered = []
            for fb in self.feedback_store:
                if fb.feedback_score >= min_score:
                    if include_implicit or "implicit" not in fb.tags:
                        filtered.append(fb)
            
            # Sort by score (highest first)
            filtered.sort(key=lambda x: x.feedback_score, reverse=True)
            
            # Limit samples
            samples = filtered[:max_samples]
            
            # Convert to RLHF format
            dataset = []
            for fb in samples:
                dataset.append({
                    "prompt": fb.user_input,
                    "response": fb.archer_response,
                    "reward": fb.feedback_score,
                    "feedback_text": fb.feedback_text,
                    "tags": fb.tags,
                    "metadata": fb.metadata,
                    "feedback_id": fb.feedback_id,
                    "timestamp": fb.timestamp,
                    "is_implicit": "implicit" in fb.tags
                })
            
            logger.info(f"Generated RLHF dataset: {len(dataset)} samples (min_score: {min_score})")
            
            return dataset
            
        except Exception as e:
            logger.error(f"Failed to generate RLHF dataset: {e}")
            return []
    
    def export_feedback(self, export_format: str = "json", file_path: str = None) -> Dict[str, Any]:
        """Export feedback data."""
        try:
            if export_format == "json":
                if not file_path:
                    file_path = f"export_feedback_{int(time.time())}.json"
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([fb.to_dict() for fb in self.feedback_store], f, indent=2, ensure_ascii=False)
                
                return {
                    "success": True,
                    "format": "json",
                    "file_path": file_path,
                    "feedback_count": len(self.feedback_store)
                }
            else:
                return {"error": f"Unsupported export format: {export_format}"}
                
        except Exception as e:
            logger.error(f"Failed to export feedback: {e}")
            return {"error": str(e), "success": False}
    
    def clear_feedback(self) -> bool:
        """Clear all feedback data."""
        try:
            self.feedback_store = []
            if self._save_feedback():
                logger.info("All feedback data cleared")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to clear feedback: {e}")
            return False
    
    def get_feedback_trends(self, days: int = 7) -> Dict[str, Any]:
        """Analyze feedback trends over time."""
        try:
            if not self.feedback_store:
                return {"error": "No feedback data available"}
            
            # Calculate time range
            cutoff = time.time() - (days * 24 * 60 * 60)
            recent_feedback = [fb for fb in self.feedback_store if fb.timestamp >= cutoff]
            
            if not recent_feedback:
                return {"error": f"No feedback in last {days} days"}
            
            # Group by day
            daily_stats = {}
            for fb in recent_feedback:
                day = time.strftime("%Y-%m-%d", time.localtime(fb.timestamp))
                if day not in daily_stats:
                    daily_stats[day] = {"count": 0, "total_score": 0, "positive": 0, "negative": 0}
                
                daily_stats[day]["count"] += 1
                daily_stats[day]["total_score"] += fb.feedback_score
                
                if fb.feedback_score > 0.3:
                    daily_stats[day]["positive"] += 1
                elif fb.feedback_score < -0.3:
                    daily_stats[day]["negative"] += 1
            
            # Calculate averages and trends
            trend_data = []
            for day, stats in sorted(daily_stats.items()):
                trend_data.append({
                    "day": day,
                    "count": stats["count"],
                    "avg_score": stats["total_score"] / stats["count"],
                    "positive": stats["positive"],
                    "negative": stats["negative"],
                    "positive_pct": stats["positive"] / stats["count"] * 100
                })
            
            return {
                "days": days,
                "total_feedback": len(recent_feedback),
                "trend_data": trend_data,
                "overall_avg_score": sum(fb.feedback_score for fb in recent_feedback) / len(recent_feedback)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze feedback trends: {e}")
            return {"error": str(e)}
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """Calculate quality metrics from feedback."""
        try:
            if len(self.feedback_store) < 5:
                return {"error": "Insufficient feedback for quality metrics"}
            
            # Calculate various quality indicators
            scores = [fb.feedback_score for fb in self.feedback_store]
            
            # Basic statistics
            avg_score = sum(scores) / len(scores)
            high_quality = sum(1 for s in scores if s >= 0.7)
            low_quality = sum(1 for s in scores if s <= -0.5)
            
            # Response quality metrics
            response_lengths = []
            latencies = []
            
            for fb in self.feedback_store:
                if fb.metadata:
                    if "response_length" in fb.metadata:
                        response_lengths.append(fb.metadata["response_length"])
                    if "response_latency" in fb.metadata:
                        latencies.append(fb.metadata["response_latency"])
            
            # Calculate metrics
            metrics = {
                "overall_quality_score": round(avg_score * 100, 1),  # 0-100 scale
                "high_quality_responses": high_quality,
                "low_quality_responses": low_quality,
                "quality_ratio": round(high_quality / max(1, len(self.feedback_store)) * 100, 1),
                "average_response_length": round(sum(response_lengths) / len(response_lengths), 1) if response_lengths else 0,
                "average_response_latency": round(sum(latencies) / len(latencies), 3) if latencies else 0,
                "sample_size": len(self.feedback_store)
            }
            
            # Add quality assessment
            if metrics["overall_quality_score"] >= 80:
                metrics["quality_assessment"] = "excellent"
            elif metrics["overall_quality_score"] >= 60:
                metrics["quality_assessment"] = "good"
            elif metrics["overall_quality_score"] >= 40:
                metrics["quality_assessment"] = "fair"
            else:
                metrics["quality_assessment"] = "needs_improvement"
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate quality metrics: {e}")
            return {"error": str(e)}

# Example usage
if __name__ == "__main__":
    print("Testing FeedbackManager...")
    
    # Create manager
    manager = FeedbackManager("test_feedback_manager.json")
    
    # Test feedback collection
    manager.start_interaction("test_1", "What is the weather today?")
    manager.record_response("The weather is sunny and warm today.")
    
    # Collect explicit feedback
    feedback1 = manager.collect_explicit_feedback(0.9, "Very helpful response!", ["weather", "helpful"])
    print(f"Feedback 1: {feedback1.feedback_id if feedback1 else 'None'}")
    
    # Test another interaction
    manager.start_interaction("test_2", "Tell me a joke")
    manager.record_response("Why don't scientists trust atoms? Because they make up everything!")
    
    feedback2 = manager.collect_explicit_feedback(0.7, "Funny!", ["joke", "entertainment"])
    print(f"Feedback 2: {feedback2.feedback_id if feedback2 else 'None'}")
    
    # Get stats
    stats = manager.get_feedback_stats()
    print(f"Stats: {stats}")
    
    # Generate RLHF dataset
    dataset = manager.generate_rlhf_dataset()
    print(f"RLHF Dataset: {len(dataset)} samples")
    
    print("Test complete!")