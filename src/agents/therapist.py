"""
Therapist Agent for ARCHER.

Monitors user behavior and provides proactive emotional support.
Enhanced with BaseSpecializedAgent capabilities including memory integration.
"""

import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from src.events.bus import bus
from .base_specialized_agent import BaseSpecializedAgent

logger = logging.getLogger(__name__)


class TherapistAgent(BaseSpecializedAgent):
    """
    Proactive behavioral monitoring and emotional support agent with enhanced capabilities.

    Features:
    - Monitors user mood from vision data
    - Triggers check-ins based on patterns
    - Tracks emotional trends
    - Memory integration (VectorMemory + EpisodicMemory)
    - Standardized handle() interface
    - Error handling and fallback strategies
    """

    def __init__(self, llm_router, memory):
        """
        Initialize the Therapist agent.

        Args:
            llm_router: LLM router for generating responses
            memory: Semantic memory for tracking history
        """
        # Initialize base class
        super().__init__(name="therapist", agent_id="therapist")
        
        # Set up LLM and semantic memory
        self.llm = llm_router
        self.semantic_memory = memory

        # Mood tracking
        self.mood_history = []
        self.last_checkin_time = None
        self.checkin_cooldown = timedelta(hours=2)  # Don't spam check-ins

        # Behavior patterns
        self.activity_log = []

        # Context awareness
        self.conversation_context = {
            "last_interaction": None,
            "current_mood_trend": "neutral",
            "stress_indicators": 0,
            "engagement_level": "unknown",
        }

        # Proactive intervention settings
        self.intervention_thresholds = {
            "stress_duration": 600,  # 10 minutes of stress
            "mood_swings": 5,  # 5 rapid mood changes
            "inactivity_period": 3600,  # 1 hour of no activity
        }

        # Time-based intervention schedules
        self.scheduled_interventions = {
            "morning_checkin": {"hour": 8, "enabled": True, "last_run": None},
            "afternoon_break": {"hour": 14, "enabled": True, "last_run": None},
            "evening_reflection": {"hour": 20, "enabled": True, "last_run": None},
            "weekly_summary": {
                "day": 6,
                "hour": 18,
                "enabled": True,
                "last_run": None,
            },  # Sunday evening
        }

        logger.info("Enhanced Therapist Agent initialized with memory integration")

    def process_vision_event(self, event_type: str, data: Dict[str, Any]):
        """
        Process a vision event from the Observer.

        Args:
            event_type: Event type (e.g., "vision.emotion.detected")
            data: Event data
        """
        if event_type == "vision.emotion.detected":
            emotion = data.get("emotion", "UNKNOWN")
            self._track_emotion(emotion)

        elif event_type == "vision.posture.bad":
            self._handle_bad_posture()

        elif event_type == "vision.user.left":
            self._track_absence(data)

    def _track_emotion(self, emotion: str):
        """Track observed emotion."""
        timestamp = time.time()

        self.mood_history.append({"emotion": emotion, "timestamp": timestamp})

        # Keep last 100 observations
        if len(self.mood_history) > 100:
            self.mood_history.pop(0)

        logger.debug(f"Tracked emotion: {emotion}")

        # Check if intervention needed
        if emotion in ["STRESSED", "SAD", "ANGRY"]:
            self._consider_checkin(emotion)

    def _consider_checkin(self, trigger_emotion: str):
        """Decide if a proactive check-in is appropriate with context awareness."""

        # Check cooldown
        now = datetime.now()
        if self.last_checkin_time:
            if now - self.last_checkin_time < self.checkin_cooldown:
                logger.debug("Check-in on cooldown")
                return

        # Analyze context for intervention decision
        context_score = self._analyze_context_for_intervention(trigger_emotion)

        # Trigger check-in based on context score
        if context_score >= 0.7:  # High intervention priority
            self._initiate_proactive_intervention(trigger_emotion, context_score)
        elif context_score >= 0.4:  # Medium priority
            # Only intervene if emotion persists
            recent_threshold = time.time() - 1800  # Last 30 minutes
            recent_negative = sum(
                1
                for m in self.mood_history
                if m["timestamp"] > recent_threshold
                and m["emotion"] in ["STRESSED", "SAD", "ANGRY"]
            )
            if recent_negative >= 2:
                self._initiate_proactive_intervention(trigger_emotion, context_score)

    def _analyze_context_for_intervention(self, trigger_emotion: str) -> float:
        """Analyze current context to determine intervention priority (0-1)."""
        score = 0.0

        # Time-based context
        current_hour = datetime.now().hour
        if 2 <= current_hour <= 6:  # Late night/early morning
            score += 0.3  # Higher priority for nighttime concerns
        elif 9 <= current_hour <= 17:  # Work hours
            score += 0.1  # Moderate priority during work

        # Emotion severity
        emotion_weights = {
            "ANGRY": 0.8,
            "STRESSED": 0.6,
            "SAD": 0.7,
            "FEAR": 0.9,
            "DISGUST": 0.4,
        }
        score += emotion_weights.get(trigger_emotion, 0.2)

        # Mood trend analysis
        recent_moods = [m["emotion"] for m in self.mood_history[-10:]]
        if len(recent_moods) >= 3:
            # Check for consistent negative trend
            negative_count = sum(
                1 for m in recent_moods if m in ["STRESSED", "SAD", "ANGRY"]
            )
            if negative_count >= len(recent_moods) * 0.7:  # 70% negative
                score += 0.4

            # Check for rapid mood swings
            unique_moods = len(set(recent_moods))
            if unique_moods >= 4:  # Many different emotions recently
                score += 0.2

        # Activity context
        if self.activity_log:
            last_activity = max(self.activity_log, key=lambda x: x["timestamp"])
            time_since_activity = time.time() - last_activity["timestamp"]

            if time_since_activity > 3600:  # No activity for over an hour
                score += 0.3  # Higher priority for inactive users

        return min(score, 1.0)  # Cap at 1.0

    def _initiate_proactive_intervention(self, reason: str, context_score: float):
        """Initiate a context-aware proactive intervention."""
        logger.info(
            f"Initiating proactive intervention (reason: {reason}, context: {context_score:.2f})"
        )

        # Generate context-aware message
        message = self._generate_contextual_message(reason, context_score)

        # Log the intervention
        self.last_checkin_time = datetime.now()
        self.conversation_context["last_interaction"] = time.time()

        # Publish event to trigger conversation
        bus.publish(
            "therapist.proactive_intervention",
            {
                "message": message,
                "reason": reason,
                "context_score": context_score,
                "timestamp": time.time(),
            },
        )

        logger.info(f"PROACTIVE INTERVENTION: '{message}'")

        # Store in memory
        if hasattr(self.memory, "store_fact"):
            self.memory.store_fact(
                "therapist",
                f"intervention_{int(time.time())}",
                {
                    "reason": reason,
                    "message": message,
                    "context_score": context_score,
                    "timestamp": time.time(),
                },
            )

    def _generate_contextual_message(self, reason: str, context_score: float) -> str:
        """Generate a contextually appropriate intervention message."""
        current_hour = datetime.now().hour

        # Time-aware message variations
        if 2 <= current_hour <= 6:  # Late night
            base_messages = {
                "STRESSED": "It's late, but you seem tense. Want to talk before bed?",
                "SAD": "Late night blues? I'm here if you want to chat.",
                "ANGRY": "Something keeping you up? I'm listening.",
            }
        elif 6 <= current_hour <= 12:  # Morning
            base_messages = {
                "STRESSED": "Good morning! You seem a bit stressed today. Everything okay?",
                "SAD": "Morning! I noticed you seem down. Want to start the day with a chat?",
                "ANGRY": "Morning! You seem frustrated. Anything I can help with?",
            }
        elif 12 <= current_hour <= 17:  # Afternoon
            base_messages = {
                "STRESSED": "Afternoon check-in: you seem tense. Need a break?",
                "SAD": "Afternoon slump? I'm here if you want to talk.",
                "ANGRY": "Afternoon frustration? Let's work through it together.",
            }
        else:  # Evening
            base_messages = {
                "STRESSED": "Evening wind-down: you seem stressed. Want to decompress?",
                "SAD": "Evening quiet time - you seem down. I'm here.",
                "ANGRY": "Evening tension? Let's resolve this before bed.",
            }

        # Intensity-based variations for high context scores
        if context_score >= 0.8:
            intensity_prefixes = {
                "STRESSED": "I can see you're really stressed. ",
                "SAD": "You seem quite down. ",
                "ANGRY": "You're clearly upset. ",
            }
            base_message = base_messages.get(reason, "How are you feeling?")
            prefix = intensity_prefixes.get(reason, "")
            return prefix + base_message

        return base_messages.get(reason, "How are you feeling?")

    def check_scheduled_interventions(self):
        """Check if any scheduled interventions should be triggered."""
        now = datetime.now()

        # Daily interventions
        for intervention_name, config in self.scheduled_interventions.items():
            if not config["enabled"]:
                continue

            should_run = False

            if "hour" in config:
                # Check if it's time for this intervention
                if now.hour == config["hour"] and (
                    config["last_run"] is None
                    or now.date() != config["last_run"].date()
                ):
                    should_run = True

            if "day" in config and "hour" in config:
                # Weekly interventions
                if (
                    now.weekday() == config["day"]
                    and now.hour == config["hour"]
                    and (
                        config["last_run"] is None
                        or (now - config["last_run"]).days >= 7
                    )
                ):
                    should_run = True

            if should_run:
                self._run_scheduled_intervention(intervention_name)
                config["last_run"] = now

    def _run_scheduled_intervention(self, intervention_name: str):
        """Run a scheduled intervention."""
        messages = {
            "morning_checkin": "Good morning! How are you feeling today? Ready to start the day?",
            "afternoon_break": "Afternoon check-in: How's your day going? Need a quick break?",
            "evening_reflection": "Evening reflection: How was your day? Anything you'd like to discuss?",
            "weekly_summary": "Weekly reflection: How has your week been? Any wins or challenges to share?",
        }

        message = messages.get(intervention_name, "How are you doing?")
        reason = f"scheduled_{intervention_name}"

        logger.info(f"SCHEDULED INTERVENTION: {intervention_name}")

        bus.publish(
            "therapist.proactive_intervention",
            {
                "message": message,
                "reason": reason,
                "context_score": 0.5,  # Medium priority for scheduled
                "timestamp": time.time(),
            },
        )

    def _handle_bad_posture(self):
        """Handle bad posture detection."""
        logger.info("Bad posture detected - gentle reminder")

        # Simple reminder (not annoying)
        # In real implementation, would speak via TTS
        logger.debug("Reminder: Check your posture")

    def _track_absence(self, data: Dict[str, Any]):
        """Track when user leaves."""
        timestamp = data.get("timestamp", time.time())
        self.activity_log.append({"event": "user_left", "timestamp": timestamp})

    def get_mood_summary(self) -> Dict[str, Any]:
        """Get summary of user's recent mood."""
        if not self.mood_history:
            return {"status": "no_data"}

        # Analyze recent mood (last hour)
        recent_threshold = time.time() - 3600
        recent_moods = [
            m["emotion"] for m in self.mood_history if m["timestamp"] > recent_threshold
        ]

        if not recent_moods:
            return {"status": "no_recent_data"}

        # Count emotion types
        mood_counts = {}
        for mood in recent_moods:
            mood_counts[mood] = mood_counts.get(mood, 0) + 1

        # Determine dominant mood
        dominant_mood = max(mood_counts, key=mood_counts.get)

        return {
            "dominant_mood": dominant_mood,
            "mood_counts": mood_counts,
            "total_observations": len(recent_moods),
        }
    
    def process(self, query: str, context: Dict[str, Any]) -> str:
        """
        Process therapist queries using the standardized interface.
        
        Args:
            query: User query
            context: Additional context
            
        Returns:
            Processed response
        """
        try:
            # Get recent memories for emotional context
            recent_memories = self.get_recent_memories(limit=3)
            memory_context = "\n".join(recent_memories) if recent_memories else ""
            
            # Get current mood summary
            mood_summary = self.get_mood_summary()
            mood_context = f"Current mood: {mood_summary.get('dominant_mood', 'neutral')}" if mood_summary else ""
            
            # Combine with semantic memory context
            semantic_context = self.semantic_memory.get_context_for_llm() if hasattr(self.semantic_memory, 'get_context_for_llm') else {}
            
            # Create enhanced context
            enhanced_context = {
                **context,
                "memory_context": memory_context,
                "mood_context": mood_context,
                "semantic_context": semantic_context,
                "agent": "therapist"
            }
            
            # Get response from LLM with therapeutic focus
            response = self.llm.get_response(
                query,
                role="therapist",
                context=enhanced_context
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Therapist processing error: {e}")
            raise ProcessingError(f"Failed to process therapist query: {e}")
    
    def simple_process(self, query: str) -> str:
        """
        Simplified processing for fallback.
        """
        return f"I understand you're feeling {query}. I'm here to listen and support you."
    
    def rule_based_response(self, query: str) -> str:
        """
        Rule-based response for fallback.
        """
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["stressed", "anxious", "worried"]):
            return "I notice you're feeling stressed. Would you like to talk about what's on your mind?"
        elif any(word in query_lower for word in ["sad", "depressed", "down"]):
            return "I'm sorry you're feeling sad. Would you like to share what's bothering you?"
        elif any(word in query_lower for word in ["angry", "frustrated", "mad"]):
            return "I can see you're feeling angry. Sometimes talking about it helps. Would you like to share?"
        elif any(word in query_lower for word in ["happy", "joyful", "excited"]):
            return "That's wonderful to hear! What's making you feel happy today?"
        else:
            return "I'm here to listen and support you. How are you feeling right now?"
