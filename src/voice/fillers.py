import os
import random
import threading
import logging
from pathlib import Path
from typing import List, Optional

import sounddevice as sd
import soundfile as sf

# Set up a dedicated logger for this module
logger = logging.getLogger(__name__)

class FillerAudioPlayer:
    """
    Manages and plays short, non-blocking "filler" audio clips.

    This class loads filler audio files (e.g., "Hmm...", "Let me see...")
    from a specified directory into memory on initialization for low-latency
    playback. Playback is handled in a separate thread to avoid blocking
    the main application logic while waiting for an LLM response.
    """

    def __init__(self, fillers_dir: Path):
        """
        Initializes the player and pre-loads filler audio clips.

        Args:
            fillers_dir (Path): The directory containing .wav filler files.
        """
        self.fillers_dir = fillers_dir
        self._filler_clips: List[tuple] = []
        self.is_playing = False
        self._load_fillers()

    def _load_fillers(self):
        """
        Scans the directory for .wav files and loads them into memory.
        Defensive checks ensure the directory exists and contains audio.
        """
        if not self.fillers_dir.is_dir():
            logger.warning(f"Fillers directory not found: {self.fillers_dir}. No fillers will be available.")
            return

        for file_path in self.fillers_dir.glob("*.wav"):
            try:
                data, samplerate = sf.read(file_path, dtype='float32')
                self._filler_clips.append((data, samplerate))
                logger.info(f"Loaded filler: {file_path.name}")
            except Exception as e:
                logger.error(f"Failed to load audio file {file_path}: {e}")

        if not self._filler_clips:
            logger.warning(f"No valid .wav files found in {self.fillers_dir}. Fillers are disabled.")

    def play_random(self) -> None:
        """
        Selects and plays a random filler clip in a non-blocking background thread.
        
        This method returns immediately. It will not play a new filler if one
        is already in progress.
        """
        if not self._filler_clips or self.is_playing:
            return

        clip_data, samplerate = random.choice(self._filler_clips)

        # The playback logic is spawned in a daemon thread to prevent blocking.
        playback_thread = threading.Thread(
            target=self._play_audio, 
            args=(clip_data, samplerate),
            daemon=True
        )
        playback_thread.start()
        logger.debug("Initiated random filler playback.")

    def _play_audio(self, data, samplerate):
        """
        The actual audio playback logic, executed in a worker thread.
        Manages the 'is_playing' state flag.
        """
        try:
            self.is_playing = True
            sd.play(data, samplerate)
            sd.wait()
        except Exception as e:
            logger.error(f"Error during filler audio playback: {e}")
        finally:
            self.is_playing = False

# --- Utility for placeholder generation ---
def create_placeholder_fillers(output_dir: Path, count: int = 3):
    """
    Generates simple sine-wave based .wav files as placeholders if none exist.
    This is useful for initial setup and testing.
    """
    import numpy as np

    try:
        import scipy.io.wavfile as wavfile
    except ImportError:
        logger.error("Scipy is required to create placeholder fillers. Please run 'pip install scipy'.")
        return

    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        logger.info(f"Created filler directory: {output_dir}")

    if any(output_dir.glob("*.wav")):
        logger.info("Filler .wav files already exist. Skipping creation.")
        return

    # Audio parameters
    samplerate = 22050  # Hz
    duration = 1.0  # seconds
    frequency = 440.0  # Hz (A4 note)
    amplitude = 0.5

    t = np.linspace(0., duration, int(samplerate * duration), endpoint=False)
    audio_data = amplitude * np.sin(2. * np.pi * frequency * t)
    
    # Apply a fade-in/out to make it sound less harsh
    fade_len = int(samplerate * 0.1)
    fade_in = np.linspace(0., 1., fade_len)
    fade_out = np.linspace(1., 0., fade_len)
    audio_data[:fade_len] *= fade_in
    audio_data[-fade_len:] *= fade_out

    for i in range(1, count + 1):
        file_path = output_dir / f"filler_{i}.wav"
        # Scale to 16-bit integer format for .wav
        scaled_data = np.int16(audio_data / np.max(np.abs(audio_data)) * 32767)
        wavfile.write(file_path, samplerate, scaled_data)
        logger.info(f"Generated placeholder filler: {file_path}")


# === SIMPLE WRAPPER FOR VOICE PIPELINE ===

class FillerPlayer:
    """
    Simple wrapper for filler audio playback.
    """

    def __init__(self, fillers_dir: Optional[Path] = None):
        """Initialize the filler player."""
        if fillers_dir is None:
            fillers_dir = Path("assets/fillers")

        logger.info(f"Initializing FillerPlayer (dir: {fillers_dir})")

        # Check if directory exists
        if not fillers_dir.exists():
            logger.warning(f"Fillers directory not found: {fillers_dir}")
            logger.info("Filler audio disabled")
            self.player = None
        else:
            self.player = FillerAudioPlayer(fillers_dir)

    def play_random(self):
        """Play a random filler sound."""
        if self.player:
            self.player.play_random()
        else:
            logger.debug("Filler playback skipped (no audio files)")