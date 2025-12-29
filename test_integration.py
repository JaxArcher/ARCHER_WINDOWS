#!/usr/bin/env python
"""
Integration test for the enhanced orchestrator and memory system.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_orchestrator_basic():
    """Test basic orchestrator functionality."""
    print("=== Testing Orchestrator ===")
    
    try:
        from agents.orchestrator import Orchestrator, get_orchestrator
        
        # Create orchestrator
        orch = get_orchestrator()
        print(f"[OK] Orchestrator created: {orch}")
        
        # Test intent classification
        test_queries = [
            ("Hello there", "greetings"),
            ("I need help with stress", "health"),
            ("What about the stock market?", "finance"),
            ("Teach me something new", "learning")
        ]
        
        for query, expected_intent in test_queries:
            intent, confidence = orch.classify_intent(query)
            print(f"  Query: '{query}' -> Intent: '{intent}' (expected: '{expected_intent}')")
            if intent == expected_intent:
                print(f"    [OK] Intent classification correct")
            else:
                print(f"    [WARN] Intent mismatch")
        
        # Test agent selection
        for intent in ["greetings", "health", "finance", "learning"]:
            agent = orch.select_agent(intent)
            print(f"  Intent '{intent}' -> Agent: '{agent}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_systems():
    """Test memory systems."""
    print("\n=== Testing Memory Systems ===")
    
    try:
        # Test long-term memory
        from memory.long_term import VectorMemory, get_vector_memory
        
        vm = get_vector_memory("test_collection")
        print(f"[OK] VectorMemory created: {vm}")
        
        # Test adding and searching
        test_text = "This is a test memory about artificial intelligence."
        mem_id = vm.add(test_text, metadata={"source": "test", "category": "ai"})
        print(f"[OK] Added memory: {mem_id}")
        
        results = vm.search("artificial intelligence", limit=2)
        print(f"[OK] Search results: {len(results)} items found")
        
        # Test base memory API
        from memory.base_memory import MemoryAPI, get_memory_api
        
        memory_api = get_memory_api()
        print(f"✅ MemoryAPI created: {memory_api}")
        
        # Test unified memory operations
        mem_id = memory_api.add(
            "User is learning about Python programming",
            metadata={"source": "test", "importance": "high"},
            memory_type="learning",
            agent_id="test_agent"
        )
        print(f"✅ Added to unified memory: {mem_id}")
        
        recent = memory_api.get_recent(limit=3)
        print(f"✅ Recent memories: {len(recent)} items")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_registration():
    """Test agent registration."""
    print("\n=== Testing Agent Registration ===")
    
    try:
        from agents.orchestrator import get_orchestrator
        
        orch = get_orchestrator()
        
        # Create a simple test agent
        class TestAgent:
            def __init__(self, name):
                self.name = name
                self.agent_id = name
                
            def handle(self, query, context=None):
                return {
                    "response": f"Test agent {self.name} processed: {query}",
                    "agent": self.name,
                    "success": True
                }
        
        # Register the agent
        test_agent = TestAgent("test_agent")
        orch.register_agent("test_agent", test_agent)
        print(f"✅ Registered test agent")
        
        # Test agent info
        agent_info = orch.get_agent_info("test_agent")
        print(f"✅ Agent info: {agent_info['name']}")
        
        # Test request handling
        response = orch.handle_request("This is a test query")
        print(f"✅ Request handled: success={response['success']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent registration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all integration tests."""
    print("Running ARCHER Orchestrator Integration Tests\n")
    
    tests = [
        test_orchestrator_basic,
        test_memory_systems,
        test_agent_registration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)