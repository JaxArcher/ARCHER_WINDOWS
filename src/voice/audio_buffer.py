"""
Audio Buffer Management for ARCHER Voice Pipeline.

Handles accumulation and management of audio frames during speech recording.
"""

import logging
import numpy as np
from typing import Optional
import time

logger = logging.getLogger(__name__)


class AudioBuffer:
    """
    Manages audio frame accumulation during speech recording.

    Features:
    - Automatic overflow prevention
    - Duration tracking
    - Efficient concatenation
    """

    def __init__(self, sample_rate: int = 16000, max_duration: float = 10.0):
        """
        Initialize the audio buffer.

        Args:
            sample_rate: Audio sample rate in Hz (default: 16000)
            max_duration: Maximum recording duration in seconds (default: 10.0)
        """
        self.sample_rate = sample_rate
        self.max_duration = max_duration
        self.max_frames = int(sample_rate * max_duration)

        self.buffer: list[np.ndarray] = []
        self.total_frames = 0
        self.start_time: Optional[float] = None

        logger.debug(f"AudioBuffer initialized: {sample_rate}Hz, max {max_duration}s")

    def append(self, frame: np.ndarray) -> bool:
        """
        Append an audio frame to the buffer.

        Args:
            frame: Audio frame as numpy array (int16)

        Returns:
            True if frame was added, False if buffer is full
        """
        if self.start_time is None:
            self.start_time = time.time()

        # Check if adding this frame would exceed max duration
        if self.total_frames + len(frame) > self.max_frames:
            logger.warning(f"Audio buffer full ({self.max_duration}s), dropping oldest frames")
            self._trim_oldest(len(frame))

        self.buffer.append(frame.copy())
        self.total_frames += len(frame)

        return True

    def _trim_oldest(self, frames_needed: int):
        """Remove oldest frames to make room for new ones."""
        while self.buffer and self.total_frames + frames_needed > self.max_frames:
            removed = self.buffer.pop(0)
            self.total_frames -= len(removed)
            logger.debug(f"Trimmed {len(removed)} frames from buffer")

    def get_audio(self) -> np.ndarray:
        """
        Get the complete accumulated audio.

        Returns:
            Concatenated audio as numpy array (int16)
        """
        if not self.buffer:
            return np.array([], dtype=np.int16)

        return np.concatenate(self.buffer)

    def get_duration(self) -> float:
        """
        Get the current duration of buffered audio.

        Returns:
            Duration in seconds
        """
        return self.total_frames / self.sample_rate

    def get_elapsed_time(self) -> float:
        """
        Get elapsed time since first frame.

        Returns:
            Elapsed time in seconds, or 0 if buffer is empty
        """
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def clear(self):
        """Clear the buffer and reset state."""
        self.buffer.clear()
        self.total_frames = 0
        self.start_time = None
        logger.debug("Audio buffer cleared")

    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self.buffer) == 0

    def get_frame_count(self) -> int:
        """Get total number of frames in buffer."""
        return self.total_frames

    def __len__(self) -> int:
        """Return number of audio chunks in buffer."""
        return len(self.buffer)

    def __repr__(self) -> str:
        return (f"AudioBuffer(frames={self.total_frames}, "
                f"duration={self.get_duration():.2f}s, "
                f"chunks={len(self.buffer)})")
