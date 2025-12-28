"""
Trainer Agent for ARCHER.

Health and fitness monitoring with proactive interventions.
"""

import logging
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TrainerAgent:
    """
    Health and fitness tracking agent.

    MVP Features:
    - Sedentary time tracking
    - Exercise prompts
    - Posture monitoring
    - Basic nutrition awareness (future: vision-based food logging)
    """

    def __init__(self, llm_router, memory):
        """
        Initialize the Trainer agent.

        Args:
            llm_router: LLM router for generating responses
            memory: Semantic memory for tracking history
        """
        self.llm = llm_router
        self.memory = memory

        # Activity tracking
        self.last_movement_time = time.time()
        self.sedentary_threshold_minutes = 60  # Prompt after 1 hour
        self.posture_warnings = []

        # Exercise log
        self.exercise_log = []

        # Nutrition tracking
        self.nutrition_goals = {
            "daily_calories": 2000,
            "protein_grams": 150,
            "water_glasses": 8,
        }
        self.daily_nutrition = {"calories": 0, "protein": 0, "meals": []}

        # Exercise schedules
        self.exercise_reminders = {
            "morning_stretch": {"hour": 7, "enabled": True, "last_run": None},
            "afternoon_walk": {"hour": 15, "enabled": True, "last_run": None},
            "evening_workout": {"hour": 18, "enabled": True, "last_run": None},
        }

        logger.info("Trainer agent initialized")

    def process_vision_event(self, event_type: str, data: Dict[str, Any]):
        """
        Process a vision event from the Observer.

        Args:
            event_type: Event type
            data: Event data
        """
        if event_type == "vision.user.arrived":
            self.last_movement_time = time.time()

        elif event_type == "vision.posture.bad":
            self._handle_bad_posture()

        elif event_type == "vision.activity.detected":
            self._track_activity(data)

        elif event_type == "vision.active_analysis":
            self._process_nutrition_analysis(data)

    def _process_nutrition_analysis(self, data: Dict[str, Any]):
        """Process nutrition analysis from vision system."""
        nutrition_data = data.get("results", {}).get("nutrition")
        if not nutrition_data:
            return

        # Log detected foods
        detected_foods = nutrition_data.get("detected_foods", [])
        meal_type = nutrition_data.get("meal_type", "unknown")
        estimated_portion = nutrition_data.get("estimated_portion", 0)

        if detected_foods:
            # Estimate calories based on detected foods (basic heuristic)
            estimated_calories = self._estimate_calories_from_foods(detected_foods)

            # Log the meal
            meal_entry = {
                "type": meal_type,
                "foods": detected_foods,
                "estimated_calories": estimated_calories,
                "estimated_portion": estimated_portion,
                "timestamp": time.time(),
            }

            self.daily_nutrition["meals"].append(meal_entry)
            self.daily_nutrition["calories"] += estimated_calories

            logger.info(
                f"Nutrition detected: {meal_type} with ~{estimated_calories} calories"
            )

            # Check if over daily goal
            if (
                self.daily_nutrition["calories"]
                > self.nutrition_goals["daily_calories"] * 1.2
            ):
                self._nutrition_alert("high_calories", self.daily_nutrition["calories"])

    def _estimate_calories_from_foods(self, foods: List[Dict]) -> int:
        """Estimate calories from detected food objects."""
        calorie_estimates = {
            "apple": 95,
            "banana": 105,
            "orange": 62,
            "bowl": 0,  # Container
            "cup": 0,
            "bottle": 0,
            "plate": 0,
            "fork": 0,
            "spoon": 0,
        }

        total_calories = 0
        for food in foods:
            food_class = food.get("class", "").lower()
            confidence = food.get("confidence", 0)

            if confidence > 0.6:  # Only count confident detections
                calories = calorie_estimates.get(food_class, 100)  # Default 100 cal
                total_calories += calories

        return total_calories

    def _nutrition_alert(self, alert_type: str, value: float):
        """Send nutrition alert."""
        alerts = {
            "high_calories": f"You've consumed about {int(value)} calories today. Consider lighter options for remaining meals.",
            "low_protein": f"Your protein intake seems low today. Consider adding protein-rich foods.",
            "dehydration": "Remember to stay hydrated! Aim for 8 glasses of water daily.",
        }

        message = alerts.get(alert_type, "Nutrition check: monitor your intake.")
        logger.info(f"NUTRITION ALERT: {message}")

        # In real implementation, would trigger notification

    def check_exercise_reminders(self):
        """Check if any exercise reminders should be triggered."""
        now = datetime.now()

        for reminder_name, config in self.exercise_reminders.items():
            if not config["enabled"]:
                continue

            if now.hour == config["hour"] and (
                config["last_run"] is None or now.date() != config["last_run"].date()
            ):
                self._send_exercise_reminder(reminder_name)
                config["last_run"] = now

    def _send_exercise_reminder(self, reminder_type: str):
        """Send exercise reminder."""
        reminders = {
            "morning_stretch": "Good morning! Start your day with some gentle stretches.",
            "afternoon_walk": "Afternoon energy boost: How about a 10-minute walk?",
            "evening_workout": "Evening workout time! Even 20 minutes of activity helps.",
        }

        message = reminders.get(reminder_type, "Time for some movement!")
        logger.info(f"EXERCISE REMINDER: {message}")

        # In real implementation, would trigger notification

    def _handle_bad_posture(self):
        """Handle bad posture detection."""
        timestamp = time.time()

        self.posture_warnings.append(timestamp)

        # Keep last 100 warnings
        if len(self.posture_warnings) > 100:
            self.posture_warnings.pop(0)

        # Check if frequent bad posture
        recent_threshold = timestamp - 600  # Last 10 minutes
        recent_warnings = sum(1 for t in self.posture_warnings if t > recent_threshold)

        if recent_warnings >= 3:
            self._prompt_posture_correction()

    def _prompt_posture_correction(self):
        """Prompt user to correct posture."""
        logger.info("Prompting posture correction")

        messages = [
            "Hey, I've noticed you slouching. Mind sitting up straight?",
            "Time for a posture check! Let's straighten that back.",
            "Your posture could use some attention. Sit up tall!",
        ]

        import random

        message = random.choice(messages)

        logger.info(f"TRAINER PROMPT: {message}")

        # In real implementation, would trigger TTS or notification

    def check_sedentary_time(self):
        """Check if user has been sedentary too long."""
        elapsed_minutes = (time.time() - self.last_movement_time) / 60

        if elapsed_minutes >= self.sedentary_threshold_minutes:
            self._prompt_movement()

    def _prompt_movement(self):
        """Prompt user to move/exercise."""
        logger.info("Prompting movement (sedentary time exceeded)")

        prompts = [
            "You've been sitting for a while. How about a quick stretch?",
            "Time to move! Try 10 pushups or a quick walk.",
            "Let's get the blood flowing - stand up and stretch!",
            "Micro-workout time! 20 jumping jacks?",
        ]

        import random

        message = random.choice(prompts)

        logger.info(f"TRAINER PROMPT: {message}")

        # Reset timer
        self.last_movement_time = time.time()

    def _track_activity(self, data: Dict[str, Any]):
        """Track physical activity."""
        activity_type = data.get("type", "unknown")
        timestamp = data.get("timestamp", time.time())

        self.exercise_log.append({"activity": activity_type, "timestamp": timestamp})

        logger.info(f"Activity tracked: {activity_type}")

        # Update movement time
        self.last_movement_time = timestamp

    def log_nutrition(self, food_item: str, calories: int = 0):
        """
        Log nutrition (manual for MVP, vision-based in future).

        Args:
            food_item: Description of food
            calories: Estimated calories (optional)
        """
        entry = {"food": food_item, "calories": calories, "timestamp": time.time()}

        # Store in memory
        if hasattr(self.memory, "store_fact"):
            nutrition_log = self.memory.get_fact("trainer", "nutrition_log", [])
            nutrition_log.append(entry)
            self.memory.store_fact("trainer", "nutrition_log", nutrition_log)

        logger.info(f"Nutrition logged: {food_item} ({calories} cal)")

    def get_daily_summary(self) -> Dict[str, Any]:
        """Get daily health summary."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()

        # Count today's activities
        today_activities = [
            a for a in self.exercise_log if a["timestamp"] >= today_start
        ]

        # Count posture warnings
        today_warnings = sum(1 for t in self.posture_warnings if t >= today_start)

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "activities": len(today_activities),
            "posture_warnings": today_warnings,
            "last_movement": datetime.fromtimestamp(self.last_movement_time).strftime(
                "%H:%M"
            ),
        }
