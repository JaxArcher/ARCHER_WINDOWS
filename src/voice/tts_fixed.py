"""
Fixed TTS Manager - Simple Text-to-Speech
Avoids voice cloning to prevent "Are you listening to me?" issues
"""

import sys
import os
import tempfile
import threading
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path

class TTSEngine(Enum):
    """Available TTS engines in order of preference."""
    
    INDEX_TTS = "indextts"
    F5_TTS_BASIC = "f5_basic"  # New: Basic F5-TTS without voice cloning
    NONE = "none"

class FixedTTSManager:
    """Fixed TTS Manager that uses basic F5-TTS without voice cloning"""
    
    def __init__(self):
        self.current_engine = TTSEngine.F5_TTS_BASIC
        self._engine_instances = {}
        self._lock = threading.Lock()
        
        print("Fixed TTS Manager initialized with basic F5-TTS")
        
        # Import and cache the config
        self.config_file = Path(os.path.dirname(__file__)) / '..' / 'config' / 'f5tts_config.py'
        
        # Pre-load model if needed
        self._model = None
        self._load_model()
        
    def _load_model(self):
        """Pre-load F5-TTS model"""
        try:
            from f5_tts.api import F5TTS
            import torch
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Loading F5-TTS model on {device}...")
            
            # Load basic model without reference audio
            self._model = F5TTS(
                model="F5TTS_v1_Base",
                device=device
            )
            
            print("SUCCESS: F5-TTS model loaded")
            
        except Exception as e:
            print(f"ERROR: Failed to load F5-TTS model: {e}")
            
    def speak(self, text: str, voice: Optional[str] = None) -> bool:
        """Speak text using basic F5-TTS (no voice cloning)"""
        if not text.strip():
            return False
            
        try:
            if self.current_engine == TTSEngine.F5_TTS_BASIC:
                return self._speak_f5_basic(text, voice)
            else:
                print(f"Engine {self.current_engine.value} not implemented yet")
                return False
                
        except Exception as e:
            print(f"TTS synthesis failed: {e}")
            return False
    
    def _speak_f5_basic(self, text: str, voice: Optional[str] = None) -> bool:
        """Speak using F5-TTS basic model (no reference audio needed)"""
        try:
            from f5_tts.api import F5TTS
            import tempfile
            
            # Create output file path
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                output_file = f.name
            
            print(f"Starting basic F5-TTS inference...")
            print(f"Text: '{text}'")
            print(f"Output: {output_file}")
            
            # Generate speech with basic model (no ref_file or ref_text)
            result = self._model.infer(
                gen_text=text,
                speed=1.0
            )
            
            if result:
                print("SUCCESS: Basic F5-TTS synthesis completed")
                
                # Play audio if possible
                try:
                    from voice.tts import play_audio_file
                    if play_audio_file(output_file):
                        print("SUCCESS: Audio played")
                        return True
                    else:
                        print("WARNING: Audio playback failed")
                except Exception as e:
                    print(f"WARNING: Audio playback error: {e}")
                
                return True
            else:
                print("ERROR: No result from F5-TTS inference")
                return False
                
        except Exception as e:
            print(f"ERROR: F5-TTS synthesis failed: {e}")
            return False

# Replace the TTS Manager
def get_tts_manager():
    """Get fixed TTS manager"""
    return FixedTTSManager()
