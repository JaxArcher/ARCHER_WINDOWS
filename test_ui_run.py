#!/usr/bin/env python
"""Test that the UI can actually run"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

def test_ui_run():
    """Test that the UI can be instantiated"""
    print("Testing UI instantiation...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.archer_gui import ARCHERGUI
        
        # Create QApplication (required for Qt widgets)
        app = QApplication([])
        
        # Create GUI instance
        print("Creating ARCHERGUI instance...")
        gui = ARCHERGUI()
        
        # Test basic properties
        print(f"GUI window title: {gui.windowTitle()}")
        print(f"GUI size: {gui.width()}x{gui.height()}")
        
        # Test orb integration
        if hasattr(gui, 'orb_animation'):
            print("✅ Orb animation integrated")
            print(f"Orb state: {gui.get_orb_state()}")
        else:
            print("❌ Orb animation not found")
            return False
        
        # Test event bus connections
        from events.bus import bus
        print("✅ Event bus imported")
        
        # Test orb state change
        gui.set_orb_state("listening")
        print(f"Orb state after change: {gui.get_orb_state()}")
        
        print("✅ UI instantiation successful!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing UI run: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("ARCHER UI Run Test")
    print("=" * 50)
    
    success = test_ui_run()
    
    print("\n" + "=" * 50)
    if success:
        print("UI RUN TEST PASSED! The GUI can be instantiated and orb works.")
    else:
        print("UI RUN TEST FAILED.")
    print("=" * 50)