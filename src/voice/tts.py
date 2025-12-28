"""
ARCHER TTS System - Quick Fix to Restore GUI

Temporarily disables F5-TTS to restore working GUI with IndexTTS fallback.
"""

import logging
import os
import tempfile
import subprocess
import threading
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path

try:
    from src.platform_utils import play_audio_file
except ImportError:
    # Fallback for Windows path issues
    def play_audio_file(file_path: str) -> bool:
        """Windows audio playback fallback"""
        try:
            import winsound
            winsound.PlaySound(file_path, winsound.SND_FILENAME)
            return True
        except ImportError:
            try:
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                return True
            except ImportError:
                print(f"Audio playback not available: {file_path}")
                return False

# Configure file-based logging for debugging
log_file = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'f5tts_debug.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TTSEngine(Enum):
    """Available TTS engines in order of preference."""
    
    INDEX_TTS = "indextts"  # RESTORED as primary
    COQUI_TTS = "coqui"
    BARK_TTS = "bark"
    KOKORO_TTS = "kokoro"
    F5_TTS = "f5"  # Temporarily disabled
    NONE = "none"


class TTSConfig:
    """Configuration for TTS engines."""
    
    def __init__(self):
        # Container endpoints
        self.indextts_url = "http://indextts:7861"
        self.coqui_url = "http://coqui-tts:5002"
        self.bark_url = "http://bark-tts:5003"
        self.kokoro_url = "http://kokoro-tts:5004"
        
        # Local development fallbacks
        self.index_tts_path = Path("/mnt/d/ARCHER_SWARM/index-tts")
        self.voice_prompt = "examples/voice_01.wav"
        self.sample_rate = 24000
        self.device = "cuda:0"
        self.use_fp16 = True
        
        # Coqui TTS settings
        self.coqui_model = "tts_models/en/ljspeech/tacotron2-DDC_ph"
        
        # Bark settings
        self.bark_speaker = "v2/en_speaker_6"
        
        # Kokoro settings
        self.kokoro_voice = "af_heart"


class TTSManager:
    """TTS Manager with F5-TTS as primary."""
    
    def __init__(self):
        self.config = TTSConfig()
        self.current_engine = TTSEngine.F5_TTS  # F5-TTS as primary
        self._engine_instances = {}
        self._lock = threading.Lock()
        
        logger.info(f"TTS Manager initialized with engine: {self.current_engine.value}")
    
    def speak(self, text: str, voice: Optional[str] = None) -> bool:
        """Speak text using current engine."""
        if not text.strip():
            return False
            
        try:
            if self.current_engine == TTSEngine.F5_TTS:
                return self._speak_f5tts(text, voice)
            elif self.current_engine == TTSEngine.COQUI_TTS:
                return self._speak_coqui(text, voice)
            else:
                logger.warning(f"Engine {self.current_engine.value} not implemented yet")
                return False
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return False
    
    def _speak_f5tts(self, text: str, voice: Optional[str] = None) -> bool:
        """Speak using F5-TTS with correct API."""
        try:
            from f5_tts.api import F5TTS
            import tempfile
            import os
            import torch
            
            # F5-TTS requires reference audio for voice cloning
            # Use default reference audio from F5-TTS package
            from importlib.resources import files
            ref_audio_path = str(files("f5_tts").joinpath("infer/examples/basic/basic_ref_en.wav"))
            ref_text = "Some call me nature, others call me mother nature."
            
            # Create output file path
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                output_file = f.name
            
            # Initialize F5-TTS with minimal parameters (it handles ckpt/vocab internally)
            # Based on actual F5-TTS API source
            model = F5TTS(
                model="F5TTS_v1_Base",
                device="cuda" if torch.cuda.is_available() else "cpu"
            )
            
            # Generate speech
            logger.info(f"Starting F5-TTS inference with text: '{text}'")
            logger.info(f"Reference audio: {ref_audio_path}")
            logger.info(f"Output file: {output_file}")
            
            result = model.infer(
                ref_file=ref_audio_path,
                ref_text=ref_text,
                gen_text=text,
                file_wave=output_file,
                remove_silence=False,
                speed=1.0
            )
            
            logger.info(f"F5-TTS inference completed. Result type: {type(result)}")
            if isinstance(result, tuple):
                logger.info(f"Result tuple length: {len(result)}")
                if len(result) >= 2:
                    wav, sr = result[0], result[1]
                    logger.info(f"Audio shape: {wav.shape}, Sample rate: {sr}")
                else:
                    logger.warning("Unexpected result format from F5-TTS")
            else:
                logger.info(f"Result: {result}")
            
            # Play the generated audio
            logger.info(f"Playing audio file: {output_file}")
            if not os.path.exists(output_file):
                logger.error("Audio file was not created!")
                return False
            
            file_size = os.path.getsize(output_file)
            logger.info(f"Audio file size: {file_size} bytes")
            
            play_result = play_audio_file(output_file)
            logger.info(f"Audio playback result: {play_result}")
            
            # Don't clean up immediately - let user hear it
            logger.info("Keeping audio file for debugging - not cleaning up immediately")
            # Clean up after delay
            import time
            time.sleep(5)  # Give time for playback
            if os.path.exists(output_file):
                os.unlink(output_file)
                logger.info("Audio file cleaned up")
            
            logger.info("✅ F5-TTS synthesis completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"F5-TTS failed: {e}")
            return False
    
    def _speak_coqui(self, text: str, voice: Optional[str] = None) -> bool:
        """Fallback Coqui TTS."""
        try:
            import TTS
            from TTS.api import TTS
            
            tts = TTS(model_name=self.config.coqui_model)
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                output_path = f.name
            
            tts.tts_to_file(text=text, file_path=output_path)
            play_audio_file(output_path)
            
            logger.info("✅ Coqui TTS synthesis completed")
            return True
            
        except Exception as e:
            logger.error(f"Coqui TTS failed: {e}")
            return False
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Get engine information."""
        return {
            "current_engine": self.current_engine.value,
            "f5_tts_available": True,  # F5-TTS is primary
            "coqui_tts_available": False,
            "index_tts_available": False,  # IndexTTS disabled
            "available_engines": ["f5", "coqui"],
        }
    
    def switch_engine(self, engine: TTSEngine) -> bool:
        """Switch to different engine."""
        self.current_engine = engine
        logger.info(f"Switched to engine: {engine.value}")
        return True


# Global TTS manager instance
_tts_manager = None

def get_tts_manager() -> TTSManager:
    """Get or create TTS manager instance."""
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = TTSManager()
    return _tts_manager