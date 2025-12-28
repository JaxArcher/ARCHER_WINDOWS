"""
Voice Authentication Module for ARCHER.

This module provides the VoiceAuthenticator class, which uses SpeechBrain's
ECAPA-TDNN model to perform speaker verification. It handles user enrollment,
verification, and session management based on voice biometrics.

This version is the result of a merge between Dev-A1 and Dev-A2's drafts,
incorporating performance optimizations and enhanced logging.
"""

import logging
import os
import pickle
import time
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Optional, Any

import numpy as np
import torch

# Configure file-based logging as per task requirements
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Import PII filter from main (assuming it's available)
try:
    from src.main import PIIRedactionFilter

    pii_filter = PIIRedactionFilter()
except ImportError:
    pii_filter = None

file_handler = logging.FileHandler(log_dir / "voice_auth.log")
stream_handler = logging.StreamHandler()

if pii_filter:
    file_handler.addFilter(pii_filter)
    stream_handler.addFilter(pii_filter)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[file_handler, stream_handler],
)
logger = logging.getLogger(__name__)

# Attempt to import SpeechBrain, with clear instructions if it fails.
try:
    from speechbrain.inference.speaker import EncoderClassifier
except ImportError:
    logger.error(
        "SpeechBrain not found. Please install it with: pip install speechbrain"
    )
    raise

# --- Constants ---
DEFAULT_MODEL_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"
DEFAULT_PROFILES_DIR = "data/voice_profiles"
DEFAULT_MODEL_CACHE_DIR = "models"
EXPECTED_SAMPLE_RATE = 16000
NUM_ENROLLMENT_SAMPLES = 3
DEFAULT_SESSION_DURATION_S = float(
    os.getenv("SESSION_DURATION_S", 10.0)
)  # Configurable session duration


# --- Custom Exceptions ---
class VoiceAuthError(Exception):
    """Base exception for voice authentication errors."""

    pass


class EnrollmentError(VoiceAuthError):
    """Exception raised for errors during the enrollment process."""

    pass


class VerificationError(VoiceAuthError):
    """Exception raised for errors during the verification process."""

    pass


class ProfileNotFoundError(VoiceAuthError):
    """Exception raised when a user profile cannot be found."""

    pass


class VoiceAuthenticator:
    """
    Manages speaker enrollment, verification, and authentication sessions.

    This class provides a high-level interface to a speaker recognition model,
    handling the storage of voice profiles and managing a short-lived,
    time-based authentication session.
    """

    def __init__(
        self,
        model_source: str = DEFAULT_MODEL_SOURCE,
        profiles_dir: str = DEFAULT_PROFILES_DIR,
        device: Optional[str] = None,
    ):
        """
        Initializes the VoiceAuthenticator.

        Args:
            model_source (str): The HuggingFace model identifier for the speaker embedding model.
            profiles_dir (str): The directory to store user voice profiles.
            device (Optional[str]): The device to run the model on (e.g., "cuda", "cpu").
                                    If None, it will be auto-detected.
        """
        self.profiles_dir = Path(profiles_dir)
        self.device = device if device else self._auto_select_device()
        self.session_duration = DEFAULT_SESSION_DURATION_S

        self._similarity = torch.nn.CosineSimilarity(dim=-1, eps=1e-6)
        self._current_session: Dict[str, Any] = {"user_id": None, "expires_at": 0.0}

        try:
            # MERGED: Added `savedir` for predictable local model caching (from Dev-A2).
            model_cache_dir = Path(DEFAULT_MODEL_CACHE_DIR) / model_source.replace(
                "/", "_"
            )
            logger.info(
                f"Loading/caching model '{model_source}' in '{model_cache_dir}' onto device '{self.device}'..."
            )

            # Check if model files exist and try to load
            try:
                self.classifier = EncoderClassifier.from_hparams(
                    source=model_source,
                    savedir=str(model_cache_dir),
                    run_opts={"device": self.device},
                )
                logger.info("Model loaded successfully.")
            except Exception as load_error:
                logger.warning(
                    f"Model load failed: {load_error}, attempting redownload..."
                )

                # Try to redownload by clearing cache
                import shutil

                if model_cache_dir.exists():
                    shutil.rmtree(model_cache_dir)
                    logger.info(f"Cleared corrupted model cache: {model_cache_dir}")

                # Retry download and load
                self.classifier = EncoderClassifier.from_hparams(
                    source=model_source,
                    savedir=str(model_cache_dir),
                    run_opts={"device": self.device},
                )
                logger.info("Model redownloaded and loaded successfully.")

        except Exception as e:
            logger.warning(f"Failed to load SpeechBrain model after retry: {e}")
            logger.warning(
                "Voice authentication will be disabled due to model loading failure"
            )
            self.classifier = None  # Disable voice auth
            return  # Don't raise error, just disable functionality

        try:
            self.profiles_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.critical(
                f"Failed to create profiles directory at {self.profiles_dir}: {e}"
            )
            raise VoiceAuthError(f"Could not create profiles directory: {e}")

    def _auto_select_device(self) -> str:
        """Selects CUDA if available, otherwise CPU."""
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Auto-selected device: {dev}")
        return dev

    def enroll_user(self, user_id: str, audio_samples: List[np.ndarray]) -> bool:
        """
        Enroll a user by creating a voice profile from multiple audio samples.

        Args:
            user_id: Unique identifier for the user
            audio_samples: List of audio samples (numpy arrays) for enrollment

        Returns:
            True if enrollment successful, False otherwise

        Raises:
            EnrollmentError: If enrollment fails due to invalid input or processing error
        """
        if self.classifier is None:
            logger.warning("Voice authentication disabled - skipping enrollment")
            return False

        if not user_id or not isinstance(user_id, str):
            raise EnrollmentError("User ID must be a non-empty string.")

        if len(audio_samples) != NUM_ENROLLMENT_SAMPLES:
            raise EnrollmentError(
                f"Enrollment requires exactly {NUM_ENROLLMENT_SAMPLES} audio samples, "
                f"but {len(audio_samples)} were provided."
            )

        profile_path = self.profiles_dir / f"{user_id}_profile.pkl"
        if profile_path.exists():
            logger.warning(f"Profile for user '{user_id}' already exists. Overwriting.")

        try:
            # MERGED: Replaced loop with efficient batch processing (from Dev-A2).
            tensors = [
                torch.from_numpy(sample.astype(np.float32)) for sample in audio_samples
            ]
            stacked_tensors = torch.stack(tensors).to(self.device)

            with torch.no_grad():
                embeddings = self.classifier.encode_batch(stacked_tensors)

            averaged_embedding = torch.mean(embeddings, dim=0, keepdim=True)
            profile_embedding = averaged_embedding.squeeze().cpu().numpy()

            with open(profile_path, "wb") as f:
                pickle.dump(profile_embedding, f)

            logger.info(
                f"Successfully enrolled user '{user_id}' and saved profile to {profile_path}"
            )
            self._load_profile.cache_clear()  # Invalidate cache if user is re-enrolled
            return True

        except Exception as e:
            logger.error(
                f"An error occurred during enrollment for user '{user_id}': {e}",
                exc_info=True,
            )
            if profile_path.exists():
                profile_path.unlink()
            raise EnrollmentError(f"Failed to process audio or save profile: {e}")

    # MERGED: Added LRU cache for performance (from Dev-A2).
    @lru_cache(maxsize=32)
    def _load_profile(self, user_id: str) -> Optional[np.ndarray]:
        """Loads a user's voice profile embedding from disk with LRU caching."""
        profile_path = self.profiles_dir / f"{user_id}_profile.pkl"
        if not profile_path.exists():
            return None
        try:
            with open(profile_path, "rb") as f:
                return pickle.load(f)
        except (pickle.UnpicklingError, EOFError) as e:
            logger.error(f"Failed to load or unpickle profile for '{user_id}': {e}")
            return None

    def verify_speaker(
        self, audio_chunk: np.ndarray, user_id: str, threshold: float = 0.75
    ) -> bool:
        """
        Verifies an audio chunk against an enrolled user's voice profile.

        Args:
            audio_chunk (np.ndarray): The incoming audio to verify (16kHz, mono).
            user_id (str): The user ID to verify against.
            threshold (float): The cosine similarity threshold for a match (0.0 to 1.0).

        Returns:
            bool: True if the speaker is verified, False otherwise.

        Raises:
            VerificationError: If input validation fails.
            ProfileNotFoundError: If the specified user profile does not exist.
        """
        if self.classifier is None:
            logger.warning("Voice authentication disabled - skipping verification")
            return True  # Allow access when auth is disabled

        if not (0.0 < threshold <= 1.0):
            raise VerificationError("Threshold must be between 0.0 and 1.0.")

        profile_embedding_np = self._load_profile(user_id)
        if profile_embedding_np is None:
            raise ProfileNotFoundError(f"No profile found for user_id '{user_id}'.")

        try:
            profile_tensor = (
                torch.tensor(profile_embedding_np).unsqueeze(0).to(self.device)
            )
            audio_tensor = torch.tensor(audio_chunk).unsqueeze(0).to(self.device)

            with torch.no_grad():
                test_embedding = self.classifier.encode_batch(audio_tensor)

            score = self._similarity(profile_tensor, test_embedding).item()
            is_verified = score >= threshold

            log_msg = (
                f"Verification attempt for user '{user_id}': "
                f"Score={score:.4f}, Threshold={threshold}, "
                f"Result={'SUCCESS' if is_verified else 'FAILURE'}"
            )
            logger.info(log_msg)

            if is_verified:
                self._start_session(user_id)

            return is_verified

        except Exception as e:
            logger.error(
                f"An error occurred during verification for '{user_id}': {e}",
                exc_info=True,
            )
            raise VerificationError(f"Embedding generation or comparison failed: {e}")

    def _start_session(self, user_id: str):
        """Starts a new authentication session for the given user."""
        logger.info(f"Starting new auth session for user '{user_id}'.")
        self._current_session["user_id"] = user_id
        self._current_session["expires_at"] = time.time() + self.session_duration

    def refresh_session(self):
        """Refreshes the current session timer if a session is active."""
        if self._current_session["user_id"] is not None:
            self._current_session["expires_at"] = time.time() + self.session_duration
            logger.debug(
                f"Auth session for '{self._current_session['user_id']}' refreshed."
            )

    def end_session(self):
        """Immediately invalidates the current authentication session."""
        if self._current_session["user_id"]:
            logger.info(f"Auth session for '{self._current_session['user_id']}' ended.")
            self._current_session = {"user_id": None, "expires_at": 0.0}

    def get_authenticated_user(self) -> Optional[str]:
        """
        Checks if there is a valid, non-expired session.

        Returns:
            Optional[str]: The user_id of the authenticated user, or None.
        """
        session = self._current_session
        if session["user_id"] and time.time() < session["expires_at"]:
            return session["user_id"]

        if session["user_id"] and time.time() >= session["expires_at"]:
            logger.info(f"Auth session for '{session['user_id']}' has expired.")
            self.end_session()

        return None

    def list_enrolled_users(self) -> List[str]:
        """Returns a list of all user IDs with enrolled profiles."""
        if not self.profiles_dir.exists():
            return []
        return [
            p.stem.replace("_profile", "")
            for p in self.profiles_dir.glob("*_profile.pkl")
        ]

    def delete_user(self, user_id: str) -> bool:
        """Deletes a user's voice profile."""
        profile_path = self.profiles_dir / f"{user_id}_profile.pkl"
        if profile_path.exists():
            try:
                profile_path.unlink()
                self._load_profile.cache_clear()  # Invalidate cache
                logger.info(f"Deleted profile for user '{user_id}'.")
                if self._current_session["user_id"] == user_id:
                    self.end_session()
                return True
            except OSError as e:
                logger.error(f"Error deleting profile file for '{user_id}': {e}")
                return False
        else:
            logger.warning(
                f"Attempted to delete non-existent profile for user '{user_id}'."
            )
            return False
