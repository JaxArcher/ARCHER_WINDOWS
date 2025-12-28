"""
Speech-to-Text Module for ARCHER using Faster-Whisper.

This module provides GPU-accelerated speech transcription using the
CTranslate2-optimized Faster-Whisper implementation.
"""

import logging
import numpy as np
from pathlib import Path
from typing import Optional
import os

logger = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel
except ImportError:
    logger.error(
        "faster-whisper not installed. Install with: pip install faster-whisper"
    )
    WhisperModel = None


class SpeechToText:
    """
    Handles speech-to-text transcription using Faster-Whisper.

    Optimized for low-latency GPU inference with CUDA support.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ):
        """
        Initialize the STT engine.

        Args:
            model_name: Whisper model size (e.g., "base.en", "small.en", "medium.en")
            device: "cuda" or "cpu"
            compute_type: "float16", "int8", "int8_float16" (for GPU)
        """
        if WhisperModel is None:
            logger.warning("faster-whisper not installed - STT disabled")
            self.model = None
            return

        # Load from environment or use defaults
        self.model_name = model_name or os.getenv("FAST_WHISPER_MODEL", "base.en")
        self.device = device or os.getenv("FAST_WHISPER_DEVICE", "cuda")

        # Auto-select compute type based on device for CPU compatibility
        if compute_type:
            self.compute_type = compute_type
        else:
            env_compute = os.getenv("FAST_WHISPER_COMPUTE_TYPE")
            if env_compute:
                self.compute_type = env_compute
            elif self.device == "cpu":
                self.compute_type = "int8"  # CPU compatible
            else:
                self.compute_type = "float16"  # GPU optimized

        logger.info(f"Loading Faster-Whisper model: {self.model_name}")
        logger.info(f"Device: {self.device}, Compute Type: {self.compute_type}")

        try:
            self.model = WhisperModel(
                self.model_name, device=self.device, compute_type=self.compute_type
            )
            logger.info("Faster-Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Faster-Whisper model: {e}")
            raise

    def transcribe(
        self, audio: np.ndarray, language: str = "en", sample_rate: int = 16000
    ) -> str:
        """
        Transcribe audio to text.

        Args:
            audio: Audio data as numpy array (int16 or float32)
            language: Language code (default: "en")
            sample_rate: Audio sample rate (default: 16000 Hz)

        Returns:
            Transcribed text string
        """
        if self.model is None:
            logger.error("STT not available - faster-whisper not installed")
            return ""

        if len(audio) == 0:
            logger.warning("Empty audio provided to STT")
            return ""

        # Ensure audio is float32 for GPU processing
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Normalize audio if needed
        if np.max(np.abs(audio)) > 1.0:
            audio = audio / np.max(np.abs(audio))

        try:
            # Convert int16 to float32 if needed
            if audio.dtype == np.int16:
                audio_float = audio.astype(np.float32) / 32768.0
            else:
                audio_float = audio

            # Run transcription
            segments, info = self.model.transcribe(
                audio_float,
                language=language,
                beam_size=5,
                vad_filter=True,  # Use built-in VAD filtering
                vad_parameters=dict(
                    threshold=0.5,
                    min_speech_duration_ms=250,
                    max_speech_duration_s=float("inf"),
                    min_silence_duration_ms=400,
                    speech_pad_ms=400,
                ),
            )

            # Collect all segments into a single string
            text = " ".join([segment.text for segment in segments]).strip()

            logger.info(
                f"STT Result: '{text}' (language: {info.language}, probability: {info.language_probability:.2f})"
            )

            return text

        except Exception as e:
            logger.error(f"STT transcription failed: {e}", exc_info=True)
            return ""

    def transcribe_file(self, audio_path: str, language: str = "en") -> str:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file
            language: Language code

        Returns:
            Transcribed text
        """
        if self.model is None:
            logger.error("STT not available - faster-whisper not installed")
            return ""

        if not Path(audio_path).exists():
            logger.error(f"Audio file not found: {audio_path}")
            return ""

        try:
            segments, info = self.model.transcribe(
                audio_path, language=language, beam_size=5
            )

            text = " ".join([segment.text for segment in segments]).strip()
            logger.info(f"File STT Result: '{text}'")

            return text

        except Exception as e:
            logger.error(f"File STT failed: {e}", exc_info=True)
            return ""
