#!/usr/bin/env python
"""Test script for UI fixes"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

def test_ui_imports():
    """Test that all UI components can be imported"""
    print("Testing UI imports...")
    
    try:
        from ui.archer_gui import ARCHERGUI
        print("✅ ARCHERGUI imported successfully")
    except Exception as e:
        print(f"❌ Error importing ARCHERGUI: {e}")
        return False
    
    try:
        from ui.orb_animation import OrbAnimation
        print("✅ OrbAnimation imported successfully")
    except Exception as e:
        print(f"❌ Error importing OrbAnimation: {e}")
        return False
    
    try:
        from ui.status_display import StatusDisplay
        print("✅ StatusDisplay imported successfully")
    except Exception as e:
        print(f"❌ Error importing StatusDisplay: {e}")
        return False
    
    try:
        from events.bus import bus
        print("✅ EventBus imported successfully")
    except Exception as e:
        print(f"❌ Error importing EventBus: {e}")
        return False
    
    return True

def test_orb_states():
    """Test orb state transitions"""
    print("\nTesting orb state transitions...")
    
    try:
        from ui.orb_animation import OrbAnimation
        
        # Create orb (but don't show it)
        orb = OrbAnimation()
        
        # Test all states
        states = ["idle", "listening", "thinking", "speaking", "error"]
        for state in states:
            orb.set_state(state)
            current_state = orb.get_state()
            if current_state == state:
                print(f"✅ Orb state '{state}' working")
            else:
                print(f"❌ Orb state '{state}' failed - got '{current_state}'")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Error testing orb states: {e}")
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
            print("✅ Event bus working correctly")
            return True
        else:
            print("❌ Event bus not working")
            return False
            
    except Exception as e:
        print(f"❌ Error testing event bus: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("ARCHER UI Fix Testing")
    print("=" * 50)
    
    success = True
    success &= test_ui_imports()
    success &= test_orb_states()
    success &= test_event_bus()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! UI fixes are working.")
    else:
        print("❌ Some tests failed. Check the output above.")
    print("=" * 50)