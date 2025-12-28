import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Audio Configuration ---
try:
    _device_index_str = os.getenv("AUDIO_DEVICE_INDEX")
    AUDIO_DEVICE_INDEX = int(_device_index_str) if _device_index_str and _device_index_str.lower() != 'null' else None
except (ValueError, TypeError):
    logging.warning(f"Invalid AUDIO_DEVICE_INDEX '{_device_index_str}'. Using default device.")
    AUDIO_DEVICE_INDEX = None

SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", 16000))
CHUNK_DURATION_MS = int(os.getenv("CHUNK_DURATION_MS", 30))
if CHUNK_DURATION_MS not in [10, 20, 30]:
    raise ValueError("CHUNK_DURATION_MS must be 10, 20, or 30 for VAD compatibility.")
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)

# --- Wake Word (openWakeWord) ---
WAKE_WORD_MODEL_PATHS = [p.strip() for p in os.getenv("WAKE_WORD_MODEL_PATHS", "").split(',') if p.strip()]
WAKE_WORD_NAMES = [n.strip() for n in os.getenv("WAKE_WORD_NAMES", "").split(',') if n.strip()]
WAKE_WORD_THRESHOLD = float(os.getenv("WAKE_WORD_THRESHOLD", 0.5))

# --- Voice Authentication (SpeechBrain) ---
VOICE_AUTH_MODEL = os.getenv("VOICE_AUTH_MODEL", "speechbrain/spkrec-ecapa-voxceleb")
VOICE_PROFILE_PATH = os.getenv("VOICE_PROFILE_PATH", "./data/voice_profiles/col_profile.pkl")
VOICE_AUTH_THRESHOLD = float(os.getenv("VOICE_AUTH_THRESHOLD", 0.6))
VOICE_AUTH_REQUIRED = os.getenv("VOICE_AUTH_REQUIRED", "true").lower() in ('true', '1', 't')

# --- Pipeline Configuration ---
VERIFICATION_WINDOW_S = float(os.getenv("VERIFICATION_WINDOW_S", 2.5))
SESSION_TIMEOUT_S = float(os.getenv("SESSION_TIMEOUT_S", 10.0))

# --- Logging ---
LOG_FILE = os.getenv("LOG_FILE", "logs/voice_pipeline.log")

# --- Validation Checks ---
def validate_config():
    """Performs critical configuration checks on startup."""
    if not WAKE_WORD_MODEL_PATHS or not WAKE_WORD_NAMES:
        raise ValueError("WAKE_WORD_MODEL_PATHS and WAKE_WORD_NAMES must be set in the .env file.")
    if len(WAKE_WORD_MODEL_PATHS) != len(WAKE_WORD_NAMES):
        raise ValueError("WAKE_WORD_MODEL_PATHS and WAKE_WORD_NAMES must have the same number of entries.")
    for path in WAKE_WORD_MODEL_PATHS:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Wake word model not found at: {path}")

    # Create directories if they don't exist
    os.makedirs(os.path.dirname(VOICE_PROFILE_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    logging.info("Configuration validated successfully.")