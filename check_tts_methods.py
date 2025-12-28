#!/usr/bin/env python3
"""
Check ARCHER TTS Manager Methods
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_tts_methods():
    """Check available TTS methods"""
    print("Checking ARCHER TTS Manager Methods...")
    
    try:
        from voice.tts import get_tts_manager
        tts_manager = get_tts_manager()
        
        print(f"TTS Manager Type: {type(tts_manager)}")
        print(f"Current Engine: {tts_manager.current_engine}")
        print(f"Status: {tts_manager.status}")
        
        # List all available methods
        methods = [method for method in dir(tts_manager) if not method.startswith('_')]
        print(f"Available Methods: {methods}")
        
        # Check for synthesis methods
        synthesis_methods = [method for method in methods if 'synth' in method.lower() or 'tts' in method.lower()]
        print(f"Synthesis Methods: {synthesis_methods}")
        
        # Try to call common methods
        for method_name in ['synthesize_speech', 'synthesize', 'tts', 'speak', 'text_to_speech']:
            if hasattr(tts_manager, method_name):
                print(f"Found method: {method_name}")
                method = getattr(tts_manager, method_name)
                print(f"  Method: {method}")
                print(f"  Callable: {callable(method)}")
                
                # Try to get method signature
                try:
                    import inspect
                    sig = inspect.signature(method)
                    print(f"  Signature: {sig}")
                except:
                    print(f"  Signature: Could not determine")
        
        return True
        
    except Exception as e:
        print(f"Error checking TTS methods: {e}")
        return False

def main():
    print("ARCHER TTS Method Checker")
    print("=" * 40)
    
    if check_tts_methods():
        print("\nMethod check completed successfully")
    else:
        print("\nMethod check failed")

if __name__ == "__main__":
    main()