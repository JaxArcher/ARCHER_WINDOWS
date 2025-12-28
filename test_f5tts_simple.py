#!/usr/bin/env python3
"""
Simple F5-TTS Test with System Python
"""

import sys

def test_f5tts():
    """Test F5-TTS in system Python"""
    print("Testing F5-TTS in System Python Environment...")
    print("=" * 50)
    
    try:
        import f5_tts
        print("✓ SUCCESS: f5_tts module imported")
        
        try:
            from f5_tts.api import F5TTS
            print("✓ SUCCESS: F5TTS API imported")
            
            # Test basic initialization
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"✓ Device: {device}")
            
            model = F5TTS(
                model="F5TTS_v1_Base",
                device=device
            )
            print("✓ SUCCESS: F5TTS model initialized")
            
            # Test synthesis
            test_text = "Hello from ARCHER working TTS system"
            print(f"Testing synthesis with: '{test_text}'")
            
            # Check if reference audio exists
            try:
                from importlib.resources import files
                ref_audio = str(files("f5_tts").joinpath("infer/examples/basic/basic_ref_en.wav"))
                print(f"✓ Reference audio: {ref_audio}")
                
                # Test inference
                result = model.infer(
                    ref_file=ref_audio,
                    ref_text="Some call me nature, others call me mother nature.",
                    gen_text=test_text,
                    speed=1.0
                )
                
                if result:
                    print("✓ SUCCESS: F5-TTS inference completed")
                    print(f"✓ Generated speech successfully")
                    return True
                else:
                    print("✗ FAILED: No result from F5-TTS inference")
                    return False
                    
            except Exception as e:
                print(f"✗ ERROR: F5-TTS inference failed - {e}")
                return False
                
        except ImportError as e:
            print(f"✗ FAILED: F5TTS API import - {e}")
            return False
            
    except ImportError as e:
        print(f"✗ FAILED: f5_tts module not found - {e}")
        return False
    except Exception as e:
        print(f"✗ ERROR: Unexpected error - {e}")
        return False

def main():
    print("F5-TTS System Python Test")
    print("=" * 40)
    
    if test_f5tts():
        print("=" * 40)
        print("🎉 F5-TTS SYSTEM IS FULLY WORKING!")
        print("\nThe TTS system is properly installed and functional.")
        print("Desktop GUI should now work with voice synthesis.")
        return 0
    else:
        print("=" * 40)
        print("❌ F5-TTS SYSTEM NEEDS FIX")
        print("\nThe TTS system is not properly installed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())