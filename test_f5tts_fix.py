#!/usr/bin/env python3
"""
ARCHER F5-TTS Quick Fix - Text-Only Synthesis
Tests F5-TTS without voice cloning to avoid the "Archer, are you listening to me?" issue
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_simple_tts():
    """Test F5-TTS with simple text synthesis"""
    print("Testing F5-TTS without voice cloning...")
    print("=" * 50)
    
    try:
        from voice.tts import get_tts_manager
        tts_manager = get_tts_manager()
        print(f"TTS Manager: {tts_manager.current_engine.value}")
        
        # Test 1: Direct TTS speak call (should use general model)
        test_text = "Hello, this is ARCHER TTS test"
        print(f"Testing: '{test_text}'")
        
        # This should work with the general model instead of voice cloning
        result = tts_manager.speak(test_text, voice=None)
        
        if result:
            print("SUCCESS: F5-TTS synthesis completed")
            print("Note: Using general model, not voice cloning")
            return True
        else:
            print("FAILED: F5-TTS synthesis returned no result")
            return False
            
    except Exception as e:
        print(f"ERROR: TTS test failed - {e}")
        return False

def main():
    print("ARCHER F5-TTS Fix Test")
    print("=" * 40)
    
    if test_simple_tts():
        print("=" * 40)
        print("SUCCESS: F5-TTS is working without voice cloning")
        print("\nThis should fix the issue!")
        print("The system will use a general voice model instead of cloning.")
        print("\nTest this in the desktop GUI:")
        print("1. Type: 'Hello world'")
        print("2. Click: 'Text to Speech'")
        print("3. Should hear: Proper voice synthesis")
        return 0
    else:
        print("=" * 40)
        print("FAILED: TTS system still has issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())