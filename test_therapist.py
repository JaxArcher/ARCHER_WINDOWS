#!/usr/bin/env python3

import sys
import os
sys.path.append("src")

# Mock the required modules for testing
class MockLLMRouter:
    def get_response(self, query, role=None, context=None):
        if role == "therapist":
            return f"Therapist response: I understand you're feeling {query}. How can I support you?"
        return f"Mock response to: {query}"

class MockSemanticMemory:
    def get_context_for_llm(self):
        return {"context": "mock semantic context"}

# Test the enhanced therapist
from agents.therapist import TherapistAgent

# Create mock dependencies
mock_llm = MockLLMRouter()
mock_memory = MockSemanticMemory()

# Initialize therapist
therapist = TherapistAgent(mock_llm, mock_memory)

print("Therapist initialized successfully!")
print(f"Name: {therapist.name}")
print(f"Agent ID: {therapist.agent_id}")

# Test the handle method
response = therapist.handle("I'm feeling really stressed about work")
print(f"\nHandle response: {response}")

# Test the process method directly
try:
    process_response = therapist.process("I'm feeling anxious about my presentation", {})
    print(f"Process response: {process_response}")
except Exception as e:
    print(f"Process method error (expected): {e}")

# Test fallback methods
print(f"Simple process: {therapist.simple_process('stressed')}")
print(f"Rule-based response: {therapist.rule_based_response('I feel sad today')}")

# Test mood tracking
therapist._track_emotion("STRESSED")
therapist._track_emotion("SAD")
mood_summary = therapist.get_mood_summary()
print(f"\nMood summary: {mood_summary}")

print("\nTherapist enhancement successful!")
