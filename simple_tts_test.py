#!/usr/bin/env python3
"""
Simple ARCHER TTS Test - Windows Compatible
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_tts_simple():
    """Simple TTS test without Unicode"""
    print("Testing ARCHER TTS System...")
    
    try:
        # Test basic TTS import
        from voice.tts import get_tts_manager
        print("SUCCESS: TTS Manager imported")
        
        # Initialize
        tts_manager = get_tts_manager()
        print(f"SUCCESS: TTS Manager initialized with {tts_manager.current_engine.value}")
        
        # Test speech synthesis
        test_text = "Hello from ARCHER TTS system"
        print(f"Testing speech synthesis with: '{test_text}'")
        
        result = tts_manager.synthesize_speech(test_text)
        
        if result and result.get('success'):
            print("SUCCESS: Speech synthesis completed")
            print(f"Audio file: {result.get('audio_file')}")
            return True
        else:
            print("FAILED: Speech synthesis")
            print(f"Error: {result.get('error')}")
            return False
            
    except ImportError as e:
        print(f"FAILED: TTS import - {e}")
        return False
    except Exception as e:
        print(f"ERROR: TTS system - {e}")
        return False

def main():
    print("ARCHER TTS Integration Test")
    print("=" * 40)
    
    if test_tts_simple():
        print("=" * 40)
        print("SUCCESS: ARCHER TTS SYSTEM IS WORKING!")
        print("\nLaunch Options:")
        print("1. Integrated Desktop: launch_archer_integrated.bat")
        print("2. Web TTS Testing: http://localhost:7860")
        return 0
    else:
        print("=" * 40)
        print("FAILED: ARCHER TTS SYSTEM NEEDS FIX")
        print("\nCheck:")
        print("- TTS dependencies")
        print("- Audio system configuration")
        return 1

if __name__ == "__main__":
    sys.exit(main())