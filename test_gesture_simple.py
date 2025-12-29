#!/usr/bin/env python

"""
Simple test for gesture recognition functionality without deepface dependency.
"""

import sys
import os
import logging
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gesture_functionality():
    """Test gesture recognition functionality in isolation"""
    logger.info("Testing gesture recognition functionality...")
    
    try:
        # Import only what we need for gesture testing
        import cv2
        import mediapipe as mp
        
        # Initialize MediaPipe Hands
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Create a test frame (black image)
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Test hand detection on empty frame
        image_rgb = cv2.cvtColor(test_frame, cv2.COLOR_BGR2RGB)
        hand_results = hands.process(image_rgb)
        
        # Should have no hand landmarks on empty frame
        assert not hand_results.multi_hand_landmarks, "Empty frame should have no hand landmarks"
        
        logger.info("✅ Basic gesture recognition test passed!")
        
        # Clean up
        hands.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Gesture recognition test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_privacy_manager_basic():
    """Basic test of privacy manager without event bus"""
    logger.info("Testing PrivacyManager basic functionality...")
    
    try:
        # Import and test privacy manager
        from src.vision.privacy_manager import PrivacyManager
        
        # Create a new instance (not global)
        pm = PrivacyManager()
        
        # Test basic functionality
        assert not pm.get_consent_status(), "Initial consent should be False"
        
        pm.set_consent(True)
        assert pm.get_consent_status(), "Consent should be True after setting"
        
        # Test feature management
        pm.disable_feature("test_feature")
        assert "test_feature" in pm.get_disabled_features(), "Feature should be disabled"
        
        pm.enable_feature("test_feature")
        assert "test_feature" not in pm.get_disabled_features(), "Feature should be enabled"
        
        logger.info("✅ PrivacyManager basic test passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ PrivacyManager basic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run basic tests"""
    logger.info("Running basic Agent_ENV functionality tests...")
    logger.info("=" * 60)
    
    tests = [
        test_privacy_manager_basic,
        test_gesture_functionality,
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        logger.info("-" * 40)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    logger.info("=" * 60)
    logger.info(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 Basic functionality tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())