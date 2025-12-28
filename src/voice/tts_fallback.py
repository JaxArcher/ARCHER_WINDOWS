#!/usr/bin/env python3
"""
ARCHER TTS Fallback System - Uses PyTTSx3
Simple, reliable TTS that doesn't require FFmpeg or TorchCodec
"""

import sys
import os
import tempfile

class FallbackTTSManager:
    """Fallback TTS Manager using pyttsx3 - no FFmpeg required"""

    def __init__(self):
        self.current_engine = "pyttsx3"
        self.engine = None
        self._init_engine()

    def _init_engine(self):
        """Initialize TTS engine"""
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 180)  # Speed
            self.engine.setProperty('volume', 0.8)  # Volume
            print("SUCCESS: Fallback TTS engine (pyttsx3) initialized")
        except ImportError:
            print("ERROR: pyttsx3 not available. Installing...")
            try:
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pyttsx3"])
                import pyttsx3
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', 180)
                self.engine.setProperty('volume', 0.8)
                print("SUCCESS: Fallback TTS engine installed and initialized")
            except Exception as e:
                print(f"ERROR: Could not install/initialize pyttsx3: {e}")

    def speak(self, text: str, voice=None) -> bool:
        """Speak text using pyttsx3"""
        if not self.engine:
            print("ERROR: TTS engine not available")
            return False

        if not text.strip():
            return False

        try:
            print(f"Speaking: '{text}'")
            self.engine.say(text)
            self.engine.runAndWait()
            print("SUCCESS: TTS completed")
            return True
        except Exception as e:
            print(f"ERROR: TTS failed: {e}")
            return False

def get_tts_manager():
    """Get fallback TTS manager"""
    return FallbackTTSManager()