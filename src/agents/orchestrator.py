"""
Enhanced Orchestrator for ARCHER

Central coordinator that routes user requests to specialized agents,
manages conversation context, implements quality gates, and coordinates
multi-agent interactions with 4-tier memory system.

Features:
- Agent registration and management
- Intent classification (rule-based + LLM)
- Request routing with context preservation
- Quality gate verification
- Error handling and fallbacks
- Performance monitoring
- 4-tier memory integration
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import hashlib
import re

# Configure logging
logger = logging.getLogger(__name__)

class OrchestratorError(Exception):
    """Base exception for orchestrator errors."""
    pass

class AgentRegistrationError(OrchestratorError):
    """Error during agent registration."""
    pass

class RoutingError(OrchestratorError):
    """Error during request routing."""
    pass

class QualityGateError(OrchestratorError):
    """Error during quality verification."""
    pass

class Orchestrator:
    """
    Enhanced Orchestrator with 4-tier memory system integration.
    """
    
    def __init__(self):
        """Initialize the orchestrator with memory systems and agent registry."""
        
        # Initialize time tracking
        self.start_time = time.time()
        
        # Agent registry
        self.agents: Dict[str, Any] = {}
        self.agent_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Conversation context
        self.conversation_context: Dict[str, Any] = {
            "active_conversations": {},
            "conversation_history": [],
            "context_window": []  # Tier 1: Short-term memory
        }
        
        # Performance metrics
        self.performance_metrics: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "routing_times": [],
            "processing_times": [],
            "agent_performance": {}
        }
        
        # Initialize memory systems (will be enhanced)
        self._initialize_memory_systems()
        
        # Intent classification rules
        self.intent_rules = self._load_intent_rules()
        
        logger.info("Orchestrator initialized successfully")
        
    def _initialize_memory_systems(self):
        """Initialize the 4-tier memory system."""
        
        # Tier 1: Short-term memory (context window)
        self.short_term_memory = {
            "max_size": 50,  # Maximum context window size
            "current_size": 0,
            "items": []
        }
        
        # Tier 2: Long-term memory (will use VectorMemory)
        self.long_term_memory = None  # Placeholder for VectorMemory
        
        # Tier 3: Episodic memory
        self.episodic_memory = None  # Placeholder for EpisodicMemory
        
        # Tier 4: Semantic memory
        self.semantic_memory = None  # Placeholder for SemanticMemory
        
        # Try to import and initialize existing memory modules
        try:
            from src.memory.episodic_memory import EpisodicMemory
            self.episodic_memory = EpisodicMemory()
            logger.info("Episodic memory initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize episodic memory: {e}")
            
        try:
            from src.memory.semantic_memory import SemanticMemory
            self.semantic_memory = SemanticMemory()
            logger.info("Semantic memory initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize semantic memory: {e}")
            
        try:
            from src.memory.unified_vector_memory import UnifiedVectorMemory
            self.long_term_memory = UnifiedVectorMemory(
                collection_name="orchestrator_global",
                use_pinecone=False  # Start with ChromaDB only
            )
            logger.info("Long-term vector memory initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize vector memory: {e}")
    
    def _load_intent_rules(self) -> Dict[str, Any]:
        """Load intent classification rules."""
        
        # Default intent rules
        rules = {
            "greetings": {
                "patterns": ["hello", "hi", "greetings", "good morning"],
                "agent": "assistant",
                "priority": 1
            },
            "health": {
                "patterns": ["health", "wellness", "medical", "therapy", "stress"],
                "agent": "therapist",
                "priority": 2
            },
            "finance": {
                "patterns": ["stock", "investment", "portfolio", "market", "finance"],
                "agent": "stock_expert",
                "priority": 3
            },
            "learning": {
                "patterns": ["learn", "train", "study", "education", "skill"],
                "agent": "trainer",
                "priority": 4
            },
            "governance": {
                "patterns": ["policy", "compliance", "regulation", "governance"],
                "agent": "governance",
                "priority": 5
            },
            "general": {
                "patterns": ["help", "assist", "support", "question"],
                "agent": "assistant",
                "priority": 10
            }
        }
        
        # Try to load from file if exists
        rules_file = Path("config/orchestrator_rules.json")
        if rules_file.exists():
            try:
                with open(rules_file, "r") as f:
                    custom_rules = json.load(f)
                    rules.update(custom_rules)
                    logger.info(f"Loaded {len(custom_rules)} custom intent rules")
            except Exception as e:
                logger.error(f"Failed to load custom rules: {e}")
        
        return rules
    
    def register_agent(self, name: str, agent_instance: Any, metadata: Optional[Dict[str, Any]] = None):
        """
        Register an agent with the orchestrator.
        
        Args:
            name: Unique name for the agent
            agent_instance: The agent instance
            metadata: Additional agent metadata
            
        Raises:
            AgentRegistrationError: If registration fails
        """
        
        if not name or not isinstance(name, str):
            raise AgentRegistrationError("Agent name must be a non-empty string")
            
        if not agent_instance:
            raise AgentRegistrationError("Agent instance cannot be None")
            
        if name in self.agents:
            logger.warning(f"Agent '{name}' already registered, overwriting")
        
        # Register the agent
        self.agents[name] = agent_instance
        self.agent_metadata[name] = metadata or {}
        
        # Initialize agent-specific memory if available
        if hasattr(agent_instance, 'agent_id') and self.long_term_memory:
            agent_id = getattr(agent_instance, 'agent_id', name)
            try:
                # Create agent-specific collection
                collection_name = f"agent_{agent_id}"
                # Note: ChromaDB collections are created automatically on first use
                logger.info(f"Agent '{name}' registered with memory collection: {collection_name}")
            except Exception as e:
                logger.warning(f"Failed to create memory collection for agent '{name}': {e}")
        
        logger.info(f"Agent '{name}' registered successfully")
        
        return True
    
    def classify_intent(self, query: str) -> Tuple[str, float]:
        """
        Classify the intent of a user query.
        
        Args:
            query: User query text
            
        Returns:
            Tuple of (intent_name, confidence_score)
        """
        
        if not query or not isinstance(query, str):
            return "unknown", 0.0
            
        query_lower = query.lower()
        best_match = "unknown"
        best_score = 0.0
        
        # Rule-based classification
        for intent, rule in self.intent_rules.items():
            patterns = rule.get("patterns", [])
            
            # Check if any pattern matches
            for pattern in patterns:
                if pattern.lower() in query_lower:
                    score = 1.0 / (rule.get("priority", 10))  # Higher priority = higher score
                    if score > best_score:
                        best_score = score
                        best_match = intent
        
        # If no rule matches, use semantic analysis (placeholder)
        if best_match == "unknown":
            # TODO: Implement LLM-based intent classification
            # For now, default to general intent
            best_match = "general"
            best_score = 0.3  # Low confidence
        
        logger.debug(f"Intent classification: '{query}' -> '{best_match}' (confidence: {best_score:.2f})")
        
        return best_match, best_score
    
    def select_agent(self, intent: str) -> Optional[str]:
        """
        Select the appropriate agent for a given intent.
        
        Args:
            intent: Classified intent
            
        Returns:
            Agent name or None if no suitable agent found
        """
        
        # Map intents to agents
        intent_agent_map = {
            "greetings": "assistant",
            "health": "therapist",
            "finance": "stock_expert",
            "learning": "trainer",
            "governance": "governance",
            "general": "assistant",
            "unknown": "assistant"  # Default to assistant
        }
        
        selected_agent = intent_agent_map.get(intent, "assistant")
        
        # Check if agent is registered
        if selected_agent not in self.agents:
            logger.warning(f"Selected agent '{selected_agent}' not registered, falling back to assistant")
            selected_agent = "assistant"
        
        logger.debug(f"Agent selection: intent '{intent}' -> agent '{selected_agent}'")
        
        return selected_agent
    
    def _add_to_short_term_memory(self, query: str, response: str, context: Dict[str, Any]):
        """
        Add interaction to short-term memory (Tier 1).
        
        Args:
            query: User query
            response: Agent response
            context: Additional context
        """
        
        # Create memory item
        memory_item = {
            "timestamp": time.time(),
            "query": query,
            "response": response,
            "context": context,
            "memory_type": "short_term"
        }
        
        # Add to context window
        self.conversation_context["context_window"].append(memory_item)
        self.short_term_memory["current_size"] += 1
        
        # Enforce size limit (sliding window)
        if self.short_term_memory["current_size"] > self.short_term_memory["max_size"]:
            removed = self.conversation_context["context_window"].pop(0)
            self.short_term_memory["current_size"] -= 1
            logger.debug(f"Short-term memory: removed oldest item, current size: {self.short_term_memory['current_size']}")
        
        logger.debug(f"Added to short-term memory: {len(self.conversation_context['context_window'])} items")
    
    def _retrieve_short_term_context(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve recent context from short-term memory.
        
        Args:
            limit: Maximum number of items to retrieve
            
        Returns:
            List of recent memory items
        """
        
        recent_items = self.conversation_context["context_window"][-limit:]
        logger.debug(f"Retrieved {len(recent_items)} items from short-term memory")
        
        return recent_items
    
    def _add_to_long_term_memory(self, query: str, response: str, agent_name: str):
        """
        Add interaction to long-term memory (Tier 2).
        
        Args:
            query: User query
            response: Agent response
            agent_name: Name of the agent that handled the request
        """
        
        if not self.long_term_memory:
            logger.warning("Long-term memory not available, skipping")
            return
        
        try:
            # Create memory content
            memory_content = f"Q: {query}\nA: {response}"
            
            # Store in vector memory
            memory_id = self.long_term_memory.store_memory(
                content=memory_content,
                metadata={
                    "agent": agent_name,
                    "timestamp": datetime.now().isoformat(),
                    "memory_type": "interaction",
                    "query": query,
                    "response": response
                },
                agent_id=agent_name,
                memory_type="interaction"
            )
            
            logger.debug(f"Stored in long-term memory: {memory_id}")
            
        except Exception as e:
            logger.error(f"Failed to store in long-term memory: {e}")
    
    def _retrieve_long_term_context(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context from long-term memory.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of relevant memories
        """
        
        if not self.long_term_memory:
            logger.warning("Long-term memory not available")
            return []
        
        try:
            memories = self.long_term_memory.search_memories(
                query=query,
                limit=limit,
                use_pinecone=False  # Use ChromaDB only for now
            )
            
            logger.debug(f"Retrieved {len(memories)} items from long-term memory")
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search long-term memory: {e}")
            return []
    
    def _log_to_episodic_memory(self, query: str, response: str, agent_name: str, event_type: str = "interaction"):
        """
        Log interaction to episodic memory (Tier 3).
        
        Args:
            query: User query
            response: Agent response
            agent_name: Name of the agent
            event_type: Type of event
        """
        
        if not self.episodic_memory:
            logger.warning("Episodic memory not available, skipping")
            return
        
        try:
            self.episodic_memory.store_event(
                event_type=event_type,
                data={
                    "query": query,
                    "response": response,
                    "agent": agent_name,
                    "timestamp": datetime.now().isoformat()
                },
                metadata={
                    "source": "orchestrator",
                    "importance": "normal"
                }
            )
            
            logger.debug(f"Logged to episodic memory: {event_type}")
            
        except Exception as e:
            logger.error(f"Failed to log to episodic memory: {e}")
    
    def _update_semantic_memory(self, query: str, response: str, agent_name: str):
        """
        Update semantic memory (Tier 4) with interaction data.
        
        Args:
            query: User query
            response: Agent response
            agent_name: Name of the agent
        """
        
        if not self.semantic_memory:
            logger.warning("Semantic memory not available, skipping")
            return
        
        try:
            # Extract topics and update user profile
            topics = self._extract_topics(query)
            
            for topic in topics:
                self.semantic_memory.store_fact(
                    category="user_profile",
                    key=f"interests.{topic}",
                    value=True
                )
            
            # Record interaction
            self.semantic_memory.record_interaction(topics[0] if topics else "general")
            
            logger.debug(f"Updated semantic memory with topics: {topics}")
            
        except Exception as e:
            logger.error(f"Failed to update semantic memory: {e}")
    
    def _extract_topics(self, text: str) -> List[str]:
        """
        Extract topics from text (simple keyword-based for now).
        
        Args:
            text: Input text
            
        Returns:
            List of extracted topics
        """
        
        # Simple topic extraction - will be enhanced with NLP
        topic_keywords = {
            "health": ["health", "wellness", "medical", "therapy", "stress", "anxiety"],
            "finance": ["stock", "investment", "portfolio", "market", "money", "finance"],
            "learning": ["learn", "train", "study", "education", "skill", "knowledge"],
            "technology": ["tech", "computer", "software", "hardware", "programming"],
            "general": ["help", "assist", "support", "question", "information"]
        }
        
        text_lower = text.lower()
        found_topics = []
        
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in text_lower and topic not in found_topics:
                    found_topics.append(topic)
                    break
        
        return found_topics if found_topics else ["general"]
    
    def verify_quality(self, response: Any) -> bool:
        """
        Verify the quality of an agent's response.
        
        Args:
            response: Agent response to verify
            
        Returns:
            True if response passes quality checks, False otherwise
        """
        
        # Basic quality checks
        if response is None:
            logger.warning("Quality check failed: response is None")
            return False
        
        if isinstance(response, str) and not response.strip():
            logger.warning("Quality check failed: empty response")
            return False
        
        # Check for error indicators
        if isinstance(response, dict) and response.get("success", True) is False:
            logger.warning(f"Quality check failed: agent reported error - {response.get('error', 'unknown')}")
            return False
        
        # TODO: Add more sophisticated quality checks
        # - Response relevance
        # - Completeness
        # - Coherence
        # - Safety checks
        
        logger.debug("Quality check passed")
        return True
    
    def fallback_response(self, query: str) -> Dict[str, Any]:
        """
        Generate a fallback response when primary processing fails.
        
        Args:
            query: Original user query
            
        Returns:
            Fallback response
        """
        
        fallback_responses = [
            "I'm sorry, I encountered an issue processing your request. Let me try a different approach.",
            "I had trouble with that request. Could you please provide more details or try rephrasing?",
            "My apologies, I'm experiencing technical difficulties. Let me connect you with a different resource.",
            "I couldn't process that request successfully. Would you like me to try again or ask something else?"
        ]
        
        # Select a fallback response
        response_text = fallback_responses[self.performance_metrics["failed_requests"] % len(fallback_responses)]
        
        return {
            "success": False,
            "response": response_text,
            "fallback": True,
            "suggestion": "Please try rephrasing your request or providing more context.",
            "timestamp": datetime.now().isoformat()
        }
    
    def handle_request(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main request handling method with full memory integration.
        
        Args:
            query: User query
            context: Additional context
            
        Returns:
            Response dictionary with result and metadata
        """
        
        start_time = time.time()
        self.performance_metrics["total_requests"] += 1
        
        # Initialize response structure
        response = {
            "success": False,
            "query": query,
            "agent": None,
            "response": None,
            "context_used": {},
            "timing": {},
            "error": None
        }
        
        try:
            # Step 1: Classify intent
            intent_start = time.time()
            intent, confidence = self.classify_intent(query)
            response["timing"]["intent_classification"] = time.time() - intent_start
            response["context_used"]["intent"] = intent
            response["context_used"]["confidence"] = confidence
            
            # Step 2: Select agent
            agent_start = time.time()
            agent_name = self.select_agent(intent)
            response["timing"]["agent_selection"] = time.time() - agent_start
            response["agent"] = agent_name
            
            # Step 3: Retrieve memories
            memory_start = time.time()
            
            # Get short-term context
            short_term_context = self._retrieve_short_term_context(limit=5)
            
            # Get long-term context
            long_term_context = self._retrieve_long_term_context(query, limit=3)
            
            response["timing"]["memory_retrieval"] = time.time() - memory_start
            response["context_used"]["short_term_items"] = len(short_term_context)
            response["context_used"]["long_term_items"] = len(long_term_context)
            
            # Prepare context for agent
            agent_context = {
                "query": query,
                "intent": intent,
                "short_term_memory": short_term_context,
                "long_term_memory": long_term_context,
                "user_context": context or {}
            }
            
            # Step 4: Call agent
            agent_call_start = time.time()
            agent = self.agents.get(agent_name)
            
            if not agent:
                raise RoutingError(f"Agent '{agent_name}' not found")
            
            # Call agent's handle method
            if hasattr(agent, 'handle'):
                agent_response = agent.handle(query, agent_context)
            else:
                # Fallback for agents without handle method
                agent_response = {
                    "response": f"Agent {agent_name} received your request: {query}",
                    "agent": agent_name
                }
            
            response["timing"]["agent_processing"] = time.time() - agent_call_start
            
            # Step 5: Quality verification
            quality_start = time.time()
            if not self.verify_quality(agent_response):
                logger.warning(f"Quality check failed for query: {query}")
                return self.fallback_response(query)
            
            response["timing"]["quality_verification"] = time.time() - quality_start
            
            # Step 6: Process successful response
            response["response"] = agent_response.get("response", agent_response)
            response["success"] = True
            
            # Step 7: Update memories
            memory_update_start = time.time()
            
            # Add to short-term memory
            self._add_to_short_term_memory(query, response["response"], agent_context)
            
            # Add to long-term memory
            self._add_to_long_term_memory(query, response["response"], agent_name)
            
            # Log to episodic memory
            self._log_to_episodic_memory(query, response["response"], agent_name)
            
            # Update semantic memory
            self._update_semantic_memory(query, response["response"], agent_name)
            
            response["timing"]["memory_update"] = time.time() - memory_update_start
            
            # Update performance metrics
            self.performance_metrics["successful_requests"] += 1
            
            # Record agent performance
            agent_time = response["timing"].get("agent_processing", 0)
            if agent_name not in self.performance_metrics["agent_performance"]:
                self.performance_metrics["agent_performance"][agent_name] = {
                    "total_calls": 0,
                    "total_time": 0.0,
                    "avg_time": 0.0
                }
            
            agent_stats = self.performance_metrics["agent_performance"][agent_name]
            agent_stats["total_calls"] += 1
            agent_stats["total_time"] += agent_time
            agent_stats["avg_time"] = agent_stats["total_time"] / agent_stats["total_calls"]
            
            logger.info(f"Request handled successfully: {query[:50]}... -> {agent_name}")
            
        except Exception as e:
            # Handle any errors
            self.performance_metrics["failed_requests"] += 1
            error_msg = str(e)
            logger.error(f"Request handling failed: {error_msg}")
            
            response["error"] = error_msg
            response["response"] = self.fallback_response(query)["response"]
            
            # Log error to episodic memory
            if self.episodic_memory:
                self.episodic_memory.store_event(
                    event_type="error",
                    data={
                        "query": query,
                        "error": error_msg,
                        "timestamp": datetime.now().isoformat()
                    }
                )
        
        # Record total processing time
        response["timing"]["total"] = time.time() - start_time
        self.performance_metrics["processing_times"].append(response["timing"]["total"])
        
        return response
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        
        # Calculate averages
        metrics = self.performance_metrics.copy()
        
        if metrics["processing_times"]:
            metrics["avg_processing_time"] = sum(metrics["processing_times"]) / len(metrics["processing_times"])
        else:
            metrics["avg_processing_time"] = 0.0
            
        if metrics["total_requests"] > 0:
            metrics["success_rate"] = metrics["successful_requests"] / metrics["total_requests"]
        else:
            metrics["success_rate"] = 0.0
            
        # Add uptime
        metrics["uptime"] = time.time() - self.start_time
        
        return metrics
    
    def get_registered_agents(self) -> List[str]:
        """
        Get list of registered agents.
        
        Returns:
            List of agent names
        """
        return list(self.agents.keys())
    
    def get_agent_info(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent information or None if not found
        """
        
        if agent_name not in self.agents:
            return None
            
        return {
            "name": agent_name,
            "instance": str(type(self.agents[agent_name])),
            "metadata": self.agent_metadata.get(agent_name, {}),
            "performance": self.performance_metrics["agent_performance"].get(agent_name, {})
        }
    
    def reset_conversation_context(self):
        """Reset the conversation context."""
        
        self.conversation_context = {
            "active_conversations": {},
            "conversation_history": [],
            "context_window": []
        }
        self.short_term_memory["current_size"] = 0
        
        logger.info("Conversation context reset")
    
    def __repr__(self) -> str:
        """String representation of the orchestrator."""
        
        agents_count = len(self.agents)
        uptime = int(time.time() - self.start_time)
        success_rate = self.performance_metrics.get('success_rate', 0.0)
        
        return f"Orchestrator(agents={agents_count}, uptime={uptime}s, requests={self.performance_metrics['total_requests']}, success_rate={success_rate:.2f})"


# Global orchestrator instance
_orchestrator_instance = None


def get_orchestrator() -> Orchestrator:
    """
    Get the global orchestrator instance.
    
    Returns:
        Orchestrator instance
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = Orchestrator()
    return _orchestrator_instance


# Test the orchestrator
if __name__ == "__main__":
    # Simple test
    print("Testing Orchestrator...")
    
    # Create orchestrator
    orch = get_orchestrator()
    print(f"Orchestrator created: {orch}")
    
    # Test intent classification
    test_queries = [
        "Hello, how are you?",
        "I'm feeling stressed about work",
        "What's the stock market doing today?",
        "Can you help me learn Python?"
    ]
    
    for query in test_queries:
        intent, confidence = orch.classify_intent(query)
        print(f"Query: '{query}' -> Intent: '{intent}' (confidence: {confidence:.2f})")
    
    print("\nOrchestrator test completed successfully!")