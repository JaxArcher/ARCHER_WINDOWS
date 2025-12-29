#!/usr/bin/env python
"""
Test script for Advanced Features integration with Orchestrator.
"""

import sys
import os

# Add src to path
sys.path.insert(0, 'D:\\ARCHER_WINDOWS\\src')

def test_orchestrator_integration():
    """Test the advanced features integration with orchestrator."""
    print("=== Testing Advanced Features Orchestrator Integration ===")
    
    try:
        # Test imports
        print("\n1. Testing imports...")
        from advanced.advanced_features import AdvancedFeatures
        from advanced.plugins.visual_qa import VisualQAFeature
        from agents.orchestrator import Orchestrator
        print("SUCCESS: All imports successful")
        
        # Create instances
        print("\n2. Creating instances...")
        orchestrator = Orchestrator()
        adv_features = AdvancedFeatures()
        vqa = VisualQAFeature(enabled=True)
        print("SUCCESS: Instances created")
        
        # Register plugin with advanced features
        print("\n3. Registering plugin with advanced features...")
        adv_features.register_plugin("visual_qa", vqa, enabled=True)
        print("SUCCESS: Plugin registered with advanced features")
        
        # Register with orchestrator
        print("\n4. Registering with orchestrator...")
        adv_features.register_with_orchestrator(orchestrator)
        print("SUCCESS: Advanced features registered with orchestrator")
        
        # Check registered agents
        print("\n5. Checking registered agents...")
        registered_agents = orchestrator.get_registered_agents()
        print(f"SUCCESS: Registered agents: {registered_agents}")
        
        # Check if our advanced feature is registered
        adv_agent_found = any("adv_visual_qa" in agent for agent in registered_agents)
        if adv_agent_found:
            print("SUCCESS: Advanced visual_qa agent found in orchestrator")
        else:
            print("WARNING: Advanced visual_qa agent not found in orchestrator")
        
        # Test agent info
        print("\n6. Testing agent info...")
        agent_info = orchestrator.get_agent_info("adv_visual_qa")
        print(f"SUCCESS: Agent info: {agent_info}")
        
        print("\nSUCCESS: Orchestrator integration test completed!")
        return True
        
    except Exception as e:
        print(f"\nFAILED: Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Set up basic logging
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    success = test_orchestrator_integration()
    sys.exit(0 if success else 1)