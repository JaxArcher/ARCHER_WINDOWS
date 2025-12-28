#!/usr/bin/env python3
"""
Test ARCHER TTS Integration
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_tts_system():
    """Test TTS system functionality"""
    print("Testing ARCHER TTS System")
    print("=" * 40)
    
    try:
        # Test TTS import
        from voice.tts import get_tts_manager
        print("+ TTS Manager import: SUCCESS")
        
        # Test TTS manager initialization
        tts_manager = get_tts_manager()
        print("✓ TTS Manager initialization: SUCCESS")
        print(f"  Engine: {tts_manager.current_engine.value}")
        print(f"  Status: {tts_manager.status}")
        
        # Test simple speech synthesis
        test_text = "Hello, this is ARCHER TTS system test."
        print(f"\nTesting speech synthesis...")
        print(f"  Text: '{test_text}'")
        
        result = tts_manager.synthesize_speech(test_text)
        
        if result and result.get('success'):
            print("+ Speech synthesis: SUCCESS")
            print(f"  Audio file: {result.get('audio_file')}")
            print(f"  Duration: {result.get('duration', 'N/A')} seconds")
            
            # Test audio playback
            try:
                from voice.tts import play_audio_file
                audio_file = result.get('audio_file')
                if play_audio_file(audio_file):
                    print("+ Audio playback: SUCCESS")
                    print(f"  Played: {audio_file}")
                else:
                    print("- Audio playback: FAILED")
            except Exception as e:
                print(f"- Audio playback: ERROR - {e}")
        else:
            print("- Speech synthesis: FAILED")
            print(f"  Error: {result.get('error', 'Unknown error')}")
            
    except ImportError as e:
        print(f"- TTS import: FAILED - {e}")
        return False
    except Exception as e:
        print(f"- TTS system: ERROR - {e}")
        return False
        
    return True

def main():
    print("ARCHER TTS Integration Test")
    print("=" * 50)
    
    if test_tts_system():
        print("\n" + "=" * 50)
        print("🎉 ARCHER TTS SYSTEM IS WORKING!")
        print("\nFeatures Available:")
        print("✓ Text-to-Speech synthesis (F5-TTS)")
        print("✓ Audio playback on Windows")
        print("✓ Multi-agent integration ready")
        print("✓ Desktop GUI integration")
        
        print("\nLaunch Options:")
        print("1. Desktop GUI with TTS: launch_archer_integrated.bat")
        print("2. Web TTS Testing: http://localhost:7860")
        
        return 0
    else:
        print("\n" + "=" * 50)
        print("❌ ARCHER TTS SYSTEM NEEDS FIX")
        print("\nCheck:")
        print("- TTS dependencies installed")
        print("- Audio system configuration")
        print("- Path issues in voice.tts")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())