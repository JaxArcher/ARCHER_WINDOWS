#!/usr/bin/env python
"""
Test script for Advanced Features implementation.
"""

import sys
import os

# Add src to path
sys.path.insert(0, 'D:\\ARCHER_WINDOWS\\src')

def test_advanced_features():
    """Test the advanced features implementation."""
    print("=== Testing Advanced Features Implementation ===")
    
    try:
        # Test import
        print("\n1. Testing imports...")
        from advanced.advanced_features import AdvancedFeatures
        from advanced.plugins.visual_qa import VisualQAFeature
        print("SUCCESS: Imports successful")
        
        # Test AdvancedFeatures class
        print("\n2. Testing AdvancedFeatures class...")
        adv_features = AdvancedFeatures()
        print(f"SUCCESS: AdvancedFeatures created: {adv_features}")
        
        # Test VisualQAFeature
        print("\n3. Testing VisualQAFeature...")
        vqa = VisualQAFeature(enabled=True)
        print(f"SUCCESS: VisualQAFeature created: {vqa}")
        print(f"SUCCESS: VQA status: {vqa.get_status()}")
        
        # Test plugin registration
        print("\n4. Testing plugin registration...")
        adv_features.register_plugin("visual_qa", vqa, enabled=True)
        plugins = adv_features.get_registered_plugins()
        print(f"SUCCESS: Registered plugins: {plugins}")
        
        # Test plugin execution (with mock image)
        print("\n5. Testing plugin execution...")
        result = adv_features.execute_plugin("visual_qa", "test_image.jpg", "What is in this image?")
        print(f"SUCCESS: Plugin execution result: {result}")
        
        # Test enable/disable
        print("\n6. Testing enable/disable...")
        adv_features.disable_plugin("visual_qa")
        status = adv_features.get_plugin_status("visual_qa")
        print(f"SUCCESS: Plugin disabled: {status}")
        
        adv_features.enable_plugin("visual_qa")
        status = adv_features.get_plugin_status("visual_qa")
        print(f"SUCCESS: Plugin enabled: {status}")
        
        print("\nSUCCESS: All tests passed!")
        return True
        
    except Exception as e:
        print(f"\nFAILED: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Set up basic logging
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    success = test_advanced_features()
    sys.exit(0 if success else 1)