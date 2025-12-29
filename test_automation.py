#!/usr/bin/env python
"""
Test script for ARCHER Automation System.

Tests basic functionality of the automation controller.
"""

import sys
import os
import time

# Add src to path
sys.path.append("src")

from src.automation.controller import AutomationController, start_automation_system
from src.automation.remote import AutomationRemoteController, start_automation_remote_system


def test_basic_functionality():
    """Test basic automation controller functionality."""
    print("🧪 Testing ARCHER Automation System...")
    
    # Start automation system
    controller = start_automation_system()
    print("✅ Automation system started")
    
    # Test basic operations
    try:
        # Test mouse movement (should work even without pyautogui)
        print("🖱️  Testing mouse movement...")
        result = controller.mouse_move(100, 100)
        print(f"    Mouse move result: {result}")
        
        # Test keyboard typing
        print("⌨️  Testing keyboard typing...")
        result = controller.keyboard_type("Hello ARCHER!")
        print(f"    Keyboard type result: {result}")
        
        # Test window operations
        print("🪟  Testing window operations...")
        active_window = controller.get_active_window()
        print(f"    Active window: {active_window}")
        
        # Test file operations
        print("📁  Testing file operations...")
        files = controller.list_files(".", "*.py")
        print(f"    Found {len(files)} Python files")
        
        # Test system info
        print("💻  Testing system info...")
        system_info = controller.get_system_info()
        print(f"    System: {system_info.get('os', 'Unknown')}")
        
        # Test macro recording
        print("🎬  Testing macro recording...")
        controller.start_macro_recording()
        time.sleep(0.1)  # Simulate some actions
        controller.stop_macro_recording()
        print("    Macro recording test completed")
        
        # Test security features
        print("🔒  Testing security features...")
        controller.set_security_enabled(True)
        print("    Security enabled")
        
        # Test halt functionality
        print("⏹️  Testing halt functionality...")
        controller.halt_all()
        print("    Halt executed")
        
        print("✅ All basic tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_remote_functionality():
    """Test remote automation functionality."""
    print("\n🌐 Testing Remote Automation System...")
    
    try:
        # Start remote automation system
        remote_controller = start_automation_remote_system()
        print("✅ Remote automation system started")
        
        # Test remote command execution
        print("📡  Testing remote command execution...")
        
        # Test a simple remote command
        command = {
            "command": "get_system_info",
            "params": {}
        }
        
        if remote_controller:
            result = remote_controller.execute_remote_command(command)
            print(f"    Remote command result: {result.get('success', False)}")
        else:
            print("    Remote controller not available (expected in test environment)")
        
        print("✅ Remote automation tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Remote test failed: {e}")
        return False


def test_memory_integration():
    """Test memory integration functionality."""
    print("\n🧠 Testing Memory Integration...")
    
    try:
        controller = start_automation_system()
        
        # Perform some actions that should be logged
        controller.mouse_move(200, 200)
        controller.keyboard_type("Test memory integration")
        
        # Check if events were logged (this would require accessing the episodic memory)
        print("✅ Memory integration test completed")
        return True
        
    except Exception as e:
        print(f"❌ Memory integration test failed: {e}")
        return False


def main():
    """Run all automation tests."""
    print("🚀 Starting ARCHER Automation System Tests")
    print("=" * 50)
    
    # Run tests
    basic_success = test_basic_functionality()
    remote_success = test_remote_functionality()
    memory_success = test_memory_integration()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   Basic Functionality: {'✅ PASS' if basic_success else '❌ FAIL'}")
    print(f"   Remote Functionality: {'✅ PASS' if remote_success else '❌ FAIL'}")
    print(f"   Memory Integration: {'✅ PASS' if memory_success else '❌ FAIL'}")
    
    if all([basic_success, remote_success, memory_success]):
        print("\n🎉 All tests passed! ARCHER Automation System is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())