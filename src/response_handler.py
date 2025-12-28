"""
Response Handler Module
Connects GUI input to ARCHER backend and returns responses
"""

import logging
from src.events.bus import bus
from src.llm.router import LLMRouter
from src.vision.observer import Observer

logger = logging.getLogger(__name__)


class ResponseHandler:
    """Handles user input and generates responses"""

    def __init__(self):
        self.llm = LLMRouter()
        self.observer = None  # Will be set when vision is available
        self._setup_event_handlers()
        logger.info("Response handler initialized")

    def _setup_event_handlers(self):
        """Subscribe to events and set up handlers"""
        bus.subscribe("user.input", self._handle_user_input)
        bus.subscribe(
            "therapist.proactive_intervention", self._handle_proactive_intervention
        )
        logger.info("Subscribed to user.input and therapist events")

    def _handle_user_input(self, event):
        """Handle user input and generate response"""
        try:
            user_input = event.get("text", "")
            if not user_input.strip():
                return

            logger.info(f"Processing input: {user_input}")

            # Check for vision commands
            if self._is_vision_command(user_input):
                response = self._handle_vision_command(user_input)
            else:
                # Generate response (simplified for now)
                response = self._generate_response(user_input)

            # Emit response event
            bus.emit("assistant.response", {"text": response})
            logger.info(f"Response generated: {response}")

        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            bus.emit(
                "assistant.response",
                {"text": "Sorry, I encountered an error processing your request."},
            )

    def _is_vision_command(self, user_input):
        """Check if input is a vision-related command"""
        vision_keywords = [
            "analyze",
            "observe",
            "look",
            "see",
            "scan",
            "detect",
            "what do you see",
            "what's around",
            "describe the scene",
            "check for objects",
            "identify objects",
        ]
        return any(keyword in user_input.lower() for keyword in vision_keywords)

    def _handle_vision_command(self, user_input):
        """Handle vision-related commands"""
        if not self.observer:
            return "Vision system is not available."

        try:
            # Determine analysis type
            user_input_lower = user_input.lower()
            if "object" in user_input_lower or "detect" in user_input_lower:
                analysis_type = "objects"
            elif "detailed" in user_input_lower or "full" in user_input_lower:
                analysis_type = "full"
            else:
                analysis_type = "detailed"

            # Trigger active observation
            results = self.observer.trigger_active_observation(analysis_type)

            if "error" in results:
                return f"Sorry, I couldn't analyze the scene: {results['error']}"

            # Format response
            response_parts = []

            if "emotion" in results:
                emotion = results["emotion"]
                confidence = results.get("emotion_confidence", 0)
                if emotion != "UNKNOWN":
                    response_parts.append(
                        f"I detect that you're feeling {emotion.lower()} (confidence: {confidence:.1%})"
                    )

            if "posture" in results:
                posture = results["posture"]
                if posture == "SLOUCHING":
                    response_parts.append(
                        "I notice you're slouching - try sitting up straight!"
                    )
                elif posture == "UPRIGHT":
                    response_parts.append("Your posture looks good!")

            if "objects" in results and results["objects"]:
                objects = results["objects"][:5]  # Limit to top 5
                object_descriptions = []
                for obj in objects:
                    obj_class = obj["class"]
                    confidence = obj.get("confidence", 0)
                    object_descriptions.append(f"{obj_class} ({confidence:.1%})")

                if object_descriptions:
                    response_parts.append(
                        f"I can see: {', '.join(object_descriptions)}"
                    )

            if not response_parts:
                response_parts.append(
                    "I don't see anything notable in the current scene."
                )

            return " ".join(response_parts)

        except Exception as e:
            logger.error(f"Vision command failed: {e}")
            return "Sorry, I had trouble analyzing the scene."

    def _handle_proactive_intervention(self, event):
        """Handle proactive therapist interventions by converting to assistant responses."""
        try:
            message = event.get("message", "")
            reason = event.get("reason", "general")
            context_score = event.get("context_score", 0.0)

            if not message:
                return

            logger.info(f"Converting therapist intervention to response: {message}")

            # Add context about the intervention being proactive
            contextual_message = f"{message} (I'm checking in because I noticed you seemed {reason.lower()})"

            # Emit as assistant response
            bus.emit("assistant.response", {"text": contextual_message})
            logger.info(f"Proactive intervention delivered: {contextual_message}")

        except Exception as e:
            logger.error(f"Failed to handle proactive intervention: {e}")

    def _generate_response(self, user_input):
        """Generate response (placeholder for full LLM integration)"""
        # This is a simplified version - in production, use full LLM
        responses = {
            "are you active": "Yes, I'm active and ready to assist you!",
            "hello": "Hello! How can I help you today?",
            "hi": "Hi there! What can I do for you?",
            "test": "Test successful! I'm working correctly.",
        }

        # Return predefined response or generic one
        return responses.get(
            user_input.lower(),
            f"I received your input: '{user_input}'. Full response system coming soon!",
        )


# Global response handler instance
response_handler_instance = None

# Initialize response handler when imported
if __name__ != "__main__":
    response_handler_instance = ResponseHandler()
