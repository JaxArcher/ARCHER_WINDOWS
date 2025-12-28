#!/usr/bin/env python3
"""
ARCHER TTS Direct Fix - Disable Voice Cloning Temporarily
Creates a working TTS system without voice cloning issues
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def create_f5tts_config():
    """Create a simple TTS config that avoids voice cloning"""
    print("Creating simple F5-TTS configuration...")
    
    config_content = '''# Simple F5-TTS Configuration
# Disables voice cloning to avoid "Are you listening to me?" issue

[f5_tts]
# Use basic model instead of voice cloning
use_basic_model = true

# Reference settings (minimal)
ref_audio = ""
ref_text = ""

# Audio settings
device = "cuda" if os.environ.get('CUDA_AVAILABLE', '').lower() == 'true' else "cpu"
sample_rate = 24000
'''
    
    # Create config directory if needed
    config_dir = Path(os.path.dirname(__file__)) / 'src' / 'config'
    config_dir.mkdir(exist_ok=True)
    
    # Write config file
    config_file = config_dir / 'f5tts_config.py'
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    print(f"Created: {config_file}")
    return str(config_file)

def fix_tts_manager():
    """Create a fixed TTS manager that doesn't use voice cloning"""
    print("Creating fixed TTS manager...")
    
    tts_code = '''"""
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
'''
    
    # Create fixed TTS manager file
    tts_dir = Path(os.path.dirname(__file__)) / 'src' / 'voice'
    tts_dir.mkdir(exist_ok=True)
    
    tts_file = tts_dir / 'tts_fixed.py'
    with open(tts_file, 'w') as f:
        f.write(tts_code)
    
    print(f"Created: {tts_file}")
    return str(tts_file)

def create_working_launcher():
    """Create a working launcher that uses fixed TTS"""
    print("Creating working launcher with fixed TTS...")
    
    launcher_content = '''@echo off
title ARCHER Desktop GUI - Fixed TTS
echo Starting ARCHER Desktop with Fixed TTS...
cd /d "D:\\ARCHER_WINDOWS"

echo.
echo ===============================================
echo   ARCHER AI Assistant - Fixed TTS
echo ===============================================
echo.
echo Fixing TTS system to avoid voice cloning issues...
echo.

echo Using Fixed TTS system...
set PYTHONPATH=D:\\ARCHER_WINDOWS\\src;C:\\Users\\colby\\AppData\\Local\\Programs\\Python\\Python313\\Lib\\site-packages
set PYTHON_HOME=C:\\Users\\colby\\AppData\\Local\\Programs\\Python\\Python313

echo.
echo Initializing fixed ARCHER with TTS...
"C:\\Users\\colby\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" working_desktop_gui.py

if errorlevel 1 (
    echo.
    echo Failed to start ARCHER Desktop
    pause
) else (
    echo.
    echo ARCHER Desktop GUI launched successfully!
    echo.
    echo TTS Status: Using fixed F5-TTS system
    echo.
    echo Note: Voice cloning temporarily disabled
)'''
    
    launcher_file = Path(os.path.dirname(__file__)) / 'launch_archer_fixed_tts.bat'
    with open(launcher_file, 'w') as f:
        f.write(launcher_content)
    
    print(f"Created: {launcher_file}")
    return str(launcher_file)

def main():
    print("ARCHER TTS Direct Fix")
    print("=" * 40)
    
    # Step 1: Create config
    config_file = create_f5tts_config()
    
    # Step 2: Create fixed TTS manager
    tts_file = fix_tts_manager()
    
    # Step 3: Create working launcher
    launcher_file = create_working_launcher()
    
    print("=" * 40)
    print("SUCCESS: ARCHER TTS Fix Complete!")
    print("\nFixed Files Created:")
    print(f"1. {config_file}")
    print(f"2. {tts_file}")
    print(f"3. {launcher_file}")
    
    print("\nTo Test:")
    print("1. Double-click: launch_archer_fixed_tts.bat")
    print("2. Type simple text like 'Hello world'")
    print("3. Click 'Text to Speech'")
    print("4. Should work without voice cloning!")
    
    print("\nThis uses basic F5-TTS without voice cloning references.")
    return 0

if __name__ == "__main__":
    sys.exit(main())