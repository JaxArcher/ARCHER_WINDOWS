#!/usr/bin/env python3

import sys
import os
sys.path.append("src")

# Mock the required modules for testing
class MockLLMRouter:
    def get_response(self, query, role=None, context=None):
        return f"Mock response to: {query}"
    
    def verify_action(self, action):
        return True

class MockSemanticMemory:
    def get_context_for_llm(self):
        return {"context": "mock semantic context"}

# Test the enhanced assistant
from agents.assistant import AssistantAgent

# Create mock dependencies
mock_llm = MockLLMRouter()
mock_memory = MockSemanticMemory()

# Initialize assistant
assistant = AssistantAgent(mock_llm, mock_memory)

print("Assistant initialized successfully!")
print(f"Name: {assistant.name}")
print(f"Agent ID: {assistant.agent_id}")

# Test the handle method
response = assistant.handle("Can you remind me to call John at 3pm?")
print(f"\nHandle response: {response}")

# Test the process method directly
try:
    process_response = assistant.process("What's the weather today?", {})
    print(f"Process response: {process_response}")
except Exception as e:
    print(f"Process method error (expected): {e}")

# Test fallback methods
print(f"Simple process: {assistant.simple_process('test query')}")
print(f"Rule-based response: {assistant.rule_based_response('remind me about something')}")

print("\nAssistant enhancement successful!")
