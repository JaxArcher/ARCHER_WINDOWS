"""
Verifier System for ARCHER.

Independent model verification for critical actions.
"""

import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Verifier:
    """
    Independent verification system using separate model family.

    Ensures critical actions are safe and appropriate.
    """

    def __init__(self):
        # Use different model for verification (e.g., DeepSeek instead of LLaMA)
        self.verifier_model = os.getenv("VERIFICATION_MODEL", "deepseek-chat")
        self.verifier_api_key = os.getenv("VERIFICATION_API_KEY")
        self.verifier_base_url = os.getenv(
            "VERIFICATION_BASE_URL", "https://api.deepseek.com"
        )

        # Verification thresholds
        self.confidence_threshold = float(os.getenv("VERIFICATION_THRESHOLD", 0.8))
        self.temperature = float(os.getenv("VERIFICATION_TEMPERATURE", 0.2))

        self.client = None
        if self.verifier_api_key:
            try:
                from openai import OpenAI

                self.client = OpenAI(
                    api_key=self.verifier_api_key, base_url=self.verifier_base_url
                )
                logger.info(f"Verifier initialized with {self.verifier_model}")
            except ImportError:
                logger.warning("openai package not installed for verifier")
            except Exception as e:
                logger.error(f"Failed to initialize verifier client: {e}")
        else:
            logger.warning(
                "VERIFICATION_API_KEY not set, verifier will use mock responses"
            )

    def verify_action(
        self, action_description: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Verify if an action should be allowed.

        Args:
            action_description: Description of the action to verify
            context: Additional context for verification

        Returns:
            Dict with 'approved', 'confidence', 'reasoning'
        """
        try:
            # Create verification prompt
            prompt = self._create_verification_prompt(action_description, context)

            # Get verification response
            response = self._call_verifier_model(prompt)

            # Parse response
            result = self._parse_verification_response(response)

            logger.info(
                f"Verification result: {result['approved']} (confidence: {result['confidence']:.2f})"
            )

            return result

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            # Default to denial on error
            return {
                "approved": False,
                "confidence": 0.0,
                "reasoning": f"Verification error: {str(e)}",
            }

    def _create_verification_prompt(
        self, action: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create verification prompt."""
        context_str = ""
        if context:
            context_str = f"\nContext: {context}"

        prompt = f"""You are a critical safety verifier for an AI assistant system.

Your task is to evaluate whether the following action should be approved or denied.

ACTION TO VERIFY: {action}{context_str}

SAFETY CRITERIA:
- Does not violate privacy or security
- Does not perform unauthorized financial transactions
- Does not access sensitive personal data without explicit permission
- Does not execute system commands that could harm the user or system
- Does not send communications without user confirmation
- Does not make medical or legal claims

Respond with JSON format:
{{
    "approved": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

Be conservative - when in doubt, deny the action."""

        return prompt

    def _call_verifier_model(self, prompt: str) -> str:
        """Call the verifier model."""
        if self.client is None:
            # Fallback to mock implementation
            logger.warning("Verifier client not available, using mock response")
            if "buy" in prompt.lower() or "sell" in prompt.lower():
                return '{"approved": false, "confidence": 0.9, "reasoning": "Financial transactions require explicit user confirmation"}'
            elif "email" in prompt.lower() or "text" in prompt.lower():
                return '{"approved": false, "confidence": 0.8, "reasoning": "Communications require user approval"}'
            else:
                return '{"approved": true, "confidence": 0.95, "reasoning": "Action appears safe"}'

        try:
            response = self.client.chat.completions.create(
                model=self.verifier_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=512,
            )
            content = response.choices[0].message.content
            if content:
                return content.strip()
            else:
                logger.error("Verifier API returned empty content")
                return '{"approved": false, "confidence": 0.0, "reasoning": "Empty API response"}'
        except Exception as e:
            logger.error(f"Verifier API call failed: {e}")
            # Fallback to denial
            return (
                '{"approved": false, "confidence": 0.0, "reasoning": "API call failed"}'
            )

    def _parse_verification_response(self, response: str) -> Dict[str, Any]:
        """Parse verification response."""
        try:
            import json

            result = json.loads(response.strip())

            # Validate structure
            required_keys = ["approved", "confidence", "reasoning"]
            if not all(key in result for key in required_keys):
                raise ValueError("Missing required keys in response")

            # Validate types
            if not isinstance(result["approved"], bool):
                result["approved"] = False
            if not isinstance(result["confidence"], (int, float)):
                result["confidence"] = 0.0

            return result

        except Exception as e:
            logger.error(f"Failed to parse verification response: {e}")
            return {
                "approved": False,
                "confidence": 0.0,
                "reasoning": f"Parse error: {str(e)}",
            }

    def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        # Placeholder - would track approval rates, common denials, etc.
        return {"total_verifications": 0, "approval_rate": 0.0, "common_denials": []}
