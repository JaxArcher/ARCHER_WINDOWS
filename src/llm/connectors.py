"""
LLM Connector implementations for various providers.

Supports Anthropic Claude, Google Gemini, and Local LLM servers.
"""

import logging
import os
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMConnector(ABC):
    """Abstract base class for LLM connectors."""

    @abstractmethod
    def get_response(
        self, prompt: str, context: Optional[Dict] = None, **kwargs
    ) -> str:
        """Get a response from the LLM."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM is available."""
        pass


class AnthropicConnector(LLMConnector):
    """Connector for Anthropic Claude models."""

    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022"):
        self.model_name = model_name
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = None

        if self.api_key:
            try:
                import anthropic

                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info(f"Anthropic connector initialized: {model_name}")
            except ImportError:
                logger.warning("anthropic package not installed")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")

    def is_available(self) -> bool:
        return self.client is not None

    def get_response(
        self, prompt: str, context: Optional[Dict] = None, **kwargs
    ) -> str:
        if not self.is_available():
            raise RuntimeError("Anthropic client not available")

        try:
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 1024)

            # Build system message
            system_msg = "You are ARCHER, an advanced AI assistant. Be helpful, concise, and friendly."
            if context:
                system_msg += f"\n\nContext: {context}"

            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_msg,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text
            logger.info(f"Anthropic response ({len(response_text)} chars)")
            return response_text

        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}", exc_info=True)
            raise


class GoogleConnector(LLMConnector):
    """Connector for Google Gemini models."""

    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        self.model_name = model_name
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.client = None

        if self.api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(model_name)
                logger.info(f"Google connector initialized: {model_name}")
            except ImportError:
                logger.warning("google-generativeai package not installed")
            except Exception as e:
                logger.error(f"Failed to initialize Google client: {e}")

    def is_available(self) -> bool:
        return self.client is not None

    def get_response(
        self, prompt: str, context: Optional[Dict] = None, **kwargs
    ) -> str:
        if not self.is_available():
            raise RuntimeError("Google client not available")

        try:
            temperature = kwargs.get("temperature", 0.7)

            # Add context to prompt if provided
            full_prompt = prompt
            if context:
                full_prompt = f"Context: {context}\n\nUser: {prompt}"

            generation_config = {
                "temperature": temperature,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1024,
            }

            response = self.client.generate_content(
                full_prompt, generation_config=generation_config
            )

            response_text = response.text
            logger.info(f"Google response ({len(response_text)} chars)")
            return response_text

        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "rate limit" in error_msg or "429" in error_msg:
                logger.warning(f"Google API quota/rate limit exceeded: {e}")
                # Raise a specific exception that the router can catch for fallback
                raise RuntimeError(f"Google API quota exceeded: {e}")
            else:
                logger.error(f"Google API call failed: {e}", exc_info=True)
                raise


class LocalLLMConnector(LLMConnector):
    """Connector for local LLM servers (OpenAI-compatible API)."""

    def __init__(self, model_name: str, base_url: str = "http://169.254.123.237:1234"):
        self.model_name = model_name
        # Enforce HTTPS for non-localhost connections
        if (
            base_url.startswith("http://")
            and not base_url.startswith("http://localhost")
            and not base_url.startswith("http://127.0.0.1")
        ):
            base_url = base_url.replace("http://", "https://", 1)
            logger.info(f"Enforced HTTPS for external LLM server: {base_url}")
        self.base_url = base_url
        self.client = None

        try:
            from openai import OpenAI

            self.client = OpenAI(
                base_url=base_url,
                api_key="not-needed",  # Local server doesn't need auth
            )
            logger.info(f"Local LLM connector initialized: {model_name} at {base_url}")
        except ImportError:
            logger.warning("openai package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Local LLM client: {e}")

    def is_available(self) -> bool:
        if self.client is None:
            return False

        # Try a quick health check
        try:
            # Most local servers have a models endpoint
            models = self.client.models.list()
            return True
        except Exception:
            return False

    def get_response(
        self, prompt: str, context: Optional[Dict] = None, **kwargs
    ) -> str:
        if not self.is_available():
            raise RuntimeError("Local LLM server not available")

        try:
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 1024)

            messages = [
                {
                    "role": "system",
                    "content": "You are ARCHER, an advanced AI assistant.",
                }
            ]

            if context:
                messages.append({"role": "system", "content": f"Context: {context}"})

            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            response_text = response.choices[0].message.content
            logger.info(f"Local LLM response ({len(response_text)} chars)")
            return response_text

        except Exception as e:
            logger.error(f"Local LLM call failed: {e}", exc_info=True)
            raise
