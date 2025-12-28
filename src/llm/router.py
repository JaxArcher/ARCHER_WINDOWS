"""
LLM Router for ARCHER.

Routes requests to appropriate models based on configuration and availability.
Supports model fallback and verifier independence for critical actions.
"""

import logging
import os
import hashlib
from typing import Optional, Dict, Any
from .connectors import AnthropicConnector, GoogleConnector, LocalLLMConnector

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Routes LLM requests to appropriate models based on role and availability.

    Supports:
    - Assistant Model: General conversational responses
    - Verification Model: Critical action verification (different model family)
    - Triage Model: Quick routing and initial interpretation
    - Proactive Model: Background/observer-driven prompts
    """

    def __init__(self):
        """Initialize the LLM router with configured models."""

        # Read model configurations from environment
        # Default to LM Studio Qwen if available, fallback to Gemini
        self.assistant_model = os.getenv("ASSISTANT_MODEL", "lm_studio:qwen")
        self.verification_model = os.getenv(
            "VERIFICATION_MODEL", "claude-3-5-sonnet-20241022"
        )
        self.triage_model = os.getenv("TRIAGE_MODEL", self.assistant_model)
        self.proactive_model = os.getenv("PROACTIVE_MODEL", self.assistant_model)

        logger.info("LLM Router Configuration:")
        logger.info(f"  Assistant: {self.assistant_model}")
        logger.info(f"  Verification: {self.verification_model}")
        logger.info(f"  Triage: {self.triage_model}")
        logger.info(f"  Proactive: {self.proactive_model}")

        # Initialize connectors
        self.connectors: Dict[str, Any] = {}
        self._init_connectors()

        # Response cache for performance optimization
        self.response_cache: Dict[str, str] = {}
        self.cache_max_size = 100  # Limit cache size

        # Check for external access permission
        self.allow_external = (
            os.getenv("ALLOW_EXTERNAL_ACCESS", "false").lower() == "true"
        )
        if not self.allow_external:
            logger.warning("External access DISABLED - local models only")

    def _init_connectors(self):
        """Initialize all available model connectors."""

        # Anthropic (Claude)
        claude_connector = AnthropicConnector()
        if claude_connector.is_available():
            self.connectors["claude-3-5-sonnet-20241022"] = claude_connector
            self.connectors["claude-3-sonnet"] = claude_connector
            logger.info("✓ Anthropic connector available")

        # Google (Gemini)
        gemini_connector = GoogleConnector()
        if gemini_connector.is_available():
            self.connectors["gemini-2.0-flash-exp"] = gemini_connector
            self.connectors["gemini-2.5-flash"] = gemini_connector
            self.connectors["gemini-2.5-pro"] = gemini_connector
            logger.info("✓ Google connector available")

        # Local models (check common ones)
        for model_name in [
            "local-llama-3-8b-instr",
            "local-llama-3-70b-quant",
            "local-phi-3-mini",
            "local-deepseek-r1",
        ]:
            try:
                local_connector = LocalLLMConnector(model_name)
                if local_connector.is_available():
                    self.connectors[model_name] = local_connector
                    logger.info(f"✓ Local model available: {model_name}")
            except Exception as e:
                logger.debug(f"Local model {model_name} not available: {e}")

        # LM Studio (local OpenAI-compatible server)
        try:
            from .connectors.lm_studio_connector import LMStudioConnector

            lm_studio_connector = LMStudioConnector()
            if lm_studio_connector.is_available():
                # Add common LM Studio model names
                lm_studio_models = ["qwen", "llama-3", "mistral", "phi-3"]
                for model in lm_studio_models:
                    self.connectors[f"lm_studio:{model}"] = lm_studio_connector
                logger.info("✓ LM Studio connector available")
            else:
                logger.info(
                    "LM Studio server not detected (this is normal if not running)"
                )
        except Exception as e:
            logger.debug(f"LM Studio connector failed to initialize: {e}")

    def get_response(
        self,
        user_text: str,
        context: Optional[Dict] = None,
        role: str = "assistant",
        **kwargs,
    ) -> str:
        """
        Get a response from the appropriate model.

        Args:
            user_text: User's input text
            context: Optional context dictionary

        Returns:
            Model response string
        """
        # Check cache first for performance
        cache_key = self._generate_cache_key(user_text, context, role, kwargs)
        if cache_key in self.response_cache:
            logger.debug("Using cached response")
            return self.response_cache[cache_key]

        # Select model based on role
        model_name = self._select_model(role)

        # Get connector
        connector = self.connectors.get(model_name)
        if not connector:
            logger.error(f"No connector available for model: {model_name}")
            return "I'm sorry, but I'm unable to process your request right now."

        try:
            # Get response from model
            response = connector.get_response(user_text, context=context, **kwargs)

            # Cache the response
            self._cache_response(cache_key, response)

            return response

        except Exception as e:
            logger.error(f"Error getting response from {model_name}: {e}")
            return "I encountered an error processing your request."

    def _generate_cache_key(
        self, user_text: str, context: Optional[Dict], role: str, kwargs: Dict
    ) -> str:
        """Generate a cache key for the request."""
        key_data = f"{user_text}|{str(context)}|{role}|{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _cache_response(self, key: str, response: str):
        """Cache a response, maintaining cache size limit."""
        if len(self.response_cache) >= self.cache_max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self.response_cache))
            del self.response_cache[oldest_key]
        self.response_cache[key] = response

    def _select_model(self, role: str) -> str:
        """Select the appropriate model based on role."""
        model_map = {
            "assistant": self.assistant_model,
            "verification": self.verification_model,
            "triage": self.triage_model,
            "proactive": self.proactive_model,
        }
        return model_map.get(role, self.assistant_model)

    def _fallback_response(
        self,
        user_text: str,
        context: Optional[Dict] = None,
        role: str = "assistant",
        exclude_model: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Try fallback models if primary fails."""

        # Try any available connector
        for model_name, connector in self.connectors.items():
            # Skip excluded model
            if exclude_model and model_name == exclude_model:
                continue

            # Skip if external access blocked
            if not self.allow_external and not model_name.startswith("local-"):
                continue

            if connector.is_available():
                logger.info(f"Falling back to: {model_name}")
                try:
                    return connector.get_response(user_text, context, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    if "quota" in error_msg or "rate limit" in error_msg:
                        logger.warning(
                            f"Fallback {model_name} also quota limited, skipping"
                        )
                        continue
                    else:
                        logger.error(f"Fallback {model_name} failed: {e}")
                        continue

        # Ultimate fallback: canned response
        logger.error("All LLM models unavailable")
        return "I apologize, but I'm having trouble connecting to my language models right now. Please check your configuration or try again later."

    def verify_action(
        self, proposed_action: str, context: Optional[Dict] = None
    ) -> bool:
        """
        Verify a critical action using a different model family (verifier independence).

        Args:
            proposed_action: Description of the action to verify
            context: Optional context about the action

        Returns:
            True if action is approved, False otherwise
        """

        verification_prompt = f"""
You are a safety verifier for the ARCHER assistant. Review the following proposed action:

ACTION: {proposed_action}

Determine if this action is safe to execute. Consider:
- Does it align with user intentions?
- Are there any security or safety risks?
- Is the action reversible if needed?

Respond with only "APPROVED" or "REJECTED" followed by a brief reason.
"""

        try:
            response = self.get_response(
                verification_prompt,
                context=context,
                role="verification",
                temperature=0.2,  # Low temperature for conservative verification
            )

            # Parse response
            response_upper = response.upper()
            approved = "APPROVED" in response_upper

            logger.info(
                f"Verification result: {'APPROVED' if approved else 'REJECTED'}"
            )
            logger.info(f"Verifier reasoning: {response}")

            return approved

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            # Fail-safe: reject on error
            return False

    def get_available_models(self) -> list[str]:
        """Return list of currently available models."""
        return [name for name, conn in self.connectors.items() if conn.is_available()]
