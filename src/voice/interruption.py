"""
Interruption Handler for ARCHER (Barge-in Support).

Allows user to interrupt ARCHER while speaking.
"""

import logging
import threading
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class InterruptionDetector:
    """
    Detects user interruptions during TTS playback.

    MVP Implementation:
    - Monitors for speech activity during SPEAKING state
    - Triggers interrupt callback when detected
    """

    def __init__(self, vad, interrupt_callback: Optional[Callable] = None):
        """
        Initialize the interruption detector.

        Args:
            vad: VAD instance for speech detection
            interrupt_callback: Function to call when interruption detected
        """
        self.vad = vad
        self.interrupt_callback = interrupt_callback

        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Interruption keywords
        self.interrupt_keywords = ["stop", "halt", "archer stop"]

        logger.info("InterruptionDetector initialized")

    def start_monitoring(self):
        """Start monitoring for interruptions."""
        if self.monitoring:
            return

        self.monitoring = True
        logger.debug("Started interrupt monitoring")

    def stop_monitoring(self):
        """Stop monitoring for interruptions."""
        self.monitoring = False
        logger.debug("Stopped interrupt monitoring")

    def check_audio_frame(self, audio_frame: bytes, sample_rate: int = 16000) -> bool:
        """
        Check if an audio frame contains speech (potential interrupt).

        Args:
            audio_frame: Audio data
            sample_rate: Sample rate

        Returns:
            True if interruption detected
        """
        if not self.monitoring:
            return False

        # Check for speech activity
        if self.vad.is_speech(audio_frame, sample_rate):
            logger.info("🛑 INTERRUPTION DETECTED - User spoke during playback")

            if self.interrupt_callback:
                self.interrupt_callback()

            return True

        return False

    def check_text_input(self, text: str) -> bool:
        """
        Check if text input is an interrupt command.

        Args:
            text: User text input

        Returns:
            True if interrupt command detected
        """
        text_lower = text.lower()
        for keyword in self.interrupt_keywords:
            if keyword in text_lower:
                logger.info(f"🛑 INTERRUPT KEYWORD: '{keyword}'")
                if self.interrupt_callback:
                    self.interrupt_callback()
                return True

        return False
