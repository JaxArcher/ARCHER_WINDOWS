"""
LM Studio Connector for ARCHER LLM Integration

Provides OpenAI-compatible API interface to LM Studio running locally.
Supports Qwen and other models served through LM Studio.
"""

import os
import logging
from typing import Optional, Dict, Any
from openai import OpenAI

logger = logging.getLogger(__name__)


class LMStudioConnector:
    """
    OpenAI-compatible connector for LM Studio local LLM server.

    Supports chat completions and text generation through LM Studio's
    OpenAI-compatible API endpoint.
    """

    def __init__(
        self, base_url: str = "http://localhost:1234/v1", api_key: str = "lm-studio"
    ):
        """
        Initialize LM Studio connector.

        Args:
            base_url: LM Studio server URL (default: http://localhost:1234/v1)
            api_key: API key (LM Studio uses 'lm-studio' as default)
        """
        self.base_url = base_url
        self.api_key = api_key
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model_name = os.getenv("LM_STUDIO_MODEL", "qwen")

        logger.info(f"LM Studio connector initialized with base_url: {base_url}")

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """
        Generate text using LM Studio.

        Args:
            prompt: Input prompt
            model: Model name (defaults to LM_STUDIO_MODEL env var)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional OpenAI parameters

        Returns:
            Generated text response
        """
        try:
            model = model or self.model_name

            response = self.client.completions.create(
                model=model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )

            return response.choices[0].text.strip()

        except Exception as e:
            logger.error(f"LM Studio generation failed: {e}")
            raise

    def chat(
        self,
        messages: list,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """
        Chat completion using LM Studio.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Chat response content
        """
        try:
            model = model or self.model_name

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"LM Studio chat failed: {e}")
            raise

    def list_models(self) -> list:
        """
        List available models in LM Studio.

        Returns:
            List of model names
        """
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"Failed to list LM Studio models: {e}")
            return []

    def is_available(self) -> bool:
        """
        Check if LM Studio server is available.

        Returns:
            True if server responds, False otherwise
        """
        try:
            self.list_models()
            return True
        except:
            return False
