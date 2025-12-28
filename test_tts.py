#!/usr/bin/env python3
"""
Simple TTS test for ARCHER Windows
"""

import os
import sys
import tempfile

def test_basic_tts():
    """Test basic TTS functionality without F5-TTS dependencies"""
    
    # Test 1: Check if we can create a simple audio file
    try:
        import numpy as np
        from scipy.io.wavfile import write
        
        # Generate a simple sine wave
        sample_rate = 22050
        duration = 1.0
        frequency = 440  # A4 note
        
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        tone = 0.3 * np.sin(2 * np.pi * frequency * t)
        
        # Save to temporary file
        temp_file = os.path.join(tempfile.gettempdir(), "test_tone.wav")
        write(temp_file, sample_rate, tone.astype(np.float32))
        
        print(f"+ Created test audio file: {temp_file}")
        return True
        
    except ImportError as e:
        print(f"X Missing audio dependencies: {e}")
        return False
    except Exception as e:
        print(f"X Error creating audio: {e}")
        return False

def test_f5tts_import():
    """Test F5-TTS import without importing actual modules"""
    try:
        # Check if F5-TTS is installed
        import importlib.util
        
        f5_spec = importlib.util.find_spec("f5_tts")
        if f5_spec:
            print("✓ F5-TTS package found")
            return True
        else:
            print("X F5-TTS package not found")
            return False
            
    except Exception as e:
        print(f"X Error checking F5-TTS: {e}")
        return False

def test_gradio_integration():
    """Test Gradio integration"""
    try:
        import gradio as gr
        
        def simple_tts(text):
            return f"TTS would process: {text}"
        
        with gr.Blocks() as demo:
            gr.Markdown("# TTS Test Interface")
            text_input = gr.Textbox(label="Text to speak")
            output = gr.Textbox(label="TTS Status")
            
            btn = gr.Button("Test TTS")
            btn.click(simple_tts, text_input, output)
        
        print("✓ Gradio TTS interface created successfully")
        return True
        
    except Exception as e:
        print(f"X Gradio TTS integration failed: {e}")
        return False

def main():
    """Run all TTS tests"""
    print("ARCHER Windows TTS Testing")
    print("=" * 50)
    
    tests = [
        ("Basic Audio Generation", test_basic_tts),
        ("F5-TTS Import", test_f5tts_import), 
        ("Gradio Integration", test_gradio_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nTesting: {test_name}")
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY:")
    for test_name, result in results:
        status = "✓ PASS" if result else "X FAIL"
        print(f"  {status}: {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed - check dependencies")
        return 1

if __name__ == "__main__":
    sys.exit(main())