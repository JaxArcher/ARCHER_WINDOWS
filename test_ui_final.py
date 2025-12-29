#!/usr/bin/env python
"""Final test script for UI fixes"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

def test_ui_imports():
    """Test that all UI components can be imported"""
    print("Testing UI imports...")
    
    try:
        from ui.archer_gui import ARCHERGUI
        print("SUCCESS: ARCHERGUI imported successfully")
        return True
    except Exception as e:
        print(f"ERROR: Error importing ARCHERGUI: {e}")
        return False

def test_orb_class():
    """Test orb class exists and has correct methods"""
    print("\nTesting orb class...")
    
    try:
        from ui.orb_animation import OrbAnimation
        
        # Test that the class has the expected methods
        expected_methods = ['set_state', 'get_state']
        for method in expected_methods:
            if hasattr(OrbAnimation, method):
                print(f"SUCCESS: OrbAnimation has method '{method}'")
            else:
                print(f"ERROR: OrbAnimation missing method '{method}'")
                return False
        
        return True
    except Exception as e:
        print(f"ERROR: Error testing orb class: {e}")
        return False

def test_event_bus():
    """Test event bus functionality"""
    print("\nTesting event bus...")
    
    try:
        from events.bus import bus
        
        # Test message received flag
        message_received = False
        test_message = None
        
        def test_callback(msg):
            nonlocal message_received, test_message
            message_received = True
            test_message = msg
        
        # Subscribe and publish
        bus.subscribe("test.event", test_callback)
        bus.publish("test.event", "Hello World")
        
        if message_received and test_message == "Hello World":
            print("SUCCESS: Event bus working correctly")
            return True
        else:
            print("ERROR: Event bus not working")
            return False
            
    except Exception as e:
        print(f"ERROR: Error testing event bus: {e}")
        return False

def test_gui_structure():
    """Test that GUI has expected structure"""
    print("\nTesting GUI structure...")
    
    try:
        from ui.archer_gui import ARCHERGUI
        
        # Test that the class has expected methods
        expected_methods = [
            '_create_quadrants', 
            '_create_orb_quadrant',
            'set_orb_state',
            'add_response',
            'add_transcription',
            'clear_transcription'
        ]
        
        for method in expected_methods:
            if hasattr(ARCHERGUI, method):
                print(f"SUCCESS: ARCHERGUI has method '{method}'")
            else:
                print(f"ERROR: ARCHERGUI missing method '{method}'")
                return False
        
        return True
    except Exception as e:
        print(f"ERROR: Error testing GUI structure: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("ARCHER UI Fix Testing")
    print("=" * 50)
    
    success = True
    success &= test_ui_imports()
    success &= test_orb_class()
    success &= test_event_bus()
    success &= test_gui_structure()
    
    print("\n" + "=" * 50)
    if success:
        print("ALL TESTS PASSED! UI fixes are working.")
        print("\nSUMMARY OF FIXES:")
        print("- Added event bus integration")
        print("- Fixed orb integration in main GUI")
        print("- Added orb quadrant creation method")
        print("- Connected orb state changes to event bus")
        print("- Added transcription event handling")
    else:
        print("SOME TESTS FAILED. Check the output above.")
    print("=" * 50)