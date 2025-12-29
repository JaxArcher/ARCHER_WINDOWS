"""
Base Class for ARCHER Specialized Agents

Provides common functionality for all specialized agents including:
- Memory integration (VectorMemory and EpisodicMemory)
- Standardized handle() method interface
- Error handling and logging
- Agent registration capabilities
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Import memory systems
try:
    from src.memory.unified_vector_memory import VectorMemory
    from src.memory.episodic_memory import EpisodicMemory
    MEMORY_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Memory modules not available: {e}")
    MEMORY_AVAILABLE = False

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Base exception for agent errors."""
    pass


class InitializationError(AgentError):
    """Agent failed to initialize."""
    pass


class ProcessingError(AgentError):
    """Error during request processing."""
    pass


class MemoryError(AgentError):
    """Error accessing memory system."""
    pass


class BaseSpecializedAgent:
    """
    Base class for all ARCHER specialized agents.
    
    Provides standardized interface and common functionality:
    - Memory integration (VectorMemory + EpisodicMemory)
    - Error handling and logging
    - Standard handle() method
    - Agent registration support
    """
    
    def __init__(self, name: str, agent_id: Optional[str] = None):
        """
        Initialize the specialized agent.
        
        Args:
            name: Human-readable name of the agent
            agent_id: Unique identifier for the agent (defaults to name if None)
        """
        self.name = name
        self.agent_id = agent_id or name
        self.orchestrator = None  # Will be set by orchestrator during registration
        
        # Initialize memory systems if available
        if MEMORY_AVAILABLE:
            try:
                # Each agent gets its own memory collection
                self.memory = VectorMemory(collection_name=f"agent_{self.agent_id}")
                self.episodic = EpisodicMemory()
                logger.info(f"Memory systems initialized for {self.name}")
            except Exception as e:
                logger.error(f"Failed to initialize memory for {self.name}: {e}")
                self.memory = None
                self.episodic = None
        else:
            self.memory = None
            self.episodic = None
            logger.warning(f"Memory systems not available for {self.name}")
    
    def handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Standard interface for handling requests.
        
        Args:
            query: The user's query or request
            context: Additional context for processing
            
        Returns:
            Dict with response and metadata:
            {
                'success': bool,
                'result': Any,  # The actual response
                'agent': str,   # Agent name
                'error': Optional[str],  # Error message if any
                'error_type': Optional[str],  # Error type
                'fallback': Optional[str]  # Fallback response if error
            }
        """
        # Validate input
        if not query or not isinstance(query, str):
            logger.warning(f"{self.name}: Invalid query")
            return self._create_error_response(
                "Invalid query format",
                "validation_error"
            )
        
        if context is None:
            context = {}
        
        try:
            # Main processing - to be implemented by subclasses
            result = self.process(query, context)
            
            # Store in memory if available
            if self.memory and self.episodic:
                self._store_memory(query, result)
            
            return self._create_success_response(result)
            
        except ProcessingError as e:
            logger.error(f"{self.name} processing error: {e}")
            return self._create_error_response(
                "Processing failed",
                "processing_error",
                fallback=self.get_fallback_response(query)
            )
            
        except MemoryError as e:
            logger.error(f"{self.name} memory error: {e}")
            # Continue without memory if necessary
            try:
                result = self.process_without_memory(query, context)
                return self._create_success_response(result)
            except Exception as e:
                return self._create_error_response(
                    "Memory error occurred",
                    "memory_error",
                    fallback=self.get_fallback_response(query)
                )
                
        except Exception as e:
            logger.exception(f"{self.name} unexpected error: {e}")
            return self._create_error_response(
                "Internal error occurred",
                "unexpected_error",
                fallback=self.get_safe_fallback(query)
            )
    
    def process(self, query: str, context: Dict[str, Any]) -> Any:
        """
        Process the query with domain-specific logic.
        
        To be implemented by subclasses.
        
        Args:
            query: User query
            context: Additional context
            
        Returns:
            Processed result
        """
        raise NotImplementedError(
            f"Agent {self.name} must implement process() method"
        )
    
    def process_without_memory(self, query: str, context: Dict[str, Any]) -> Any:
        """
        Process query without memory access (fallback).
        
        To be implemented by subclasses.
        
        Args:
            query: User query
            context: Additional context
            
        Returns:
            Processed result
        """
        # Default implementation: try regular processing
        try:
            return self.process(query, context)
        except Exception:
            return self.get_fallback_response(query)
    
    def get_fallback_response(self, query: str) -> str:
        """
        Multi-level fallback strategy.
        
        Args:
            query: Original query
            
        Returns:
            Fallback response string
        """
        # Level 1: Try simplified processing
        try:
            return self.simple_process(query)
        except Exception:
            pass
        
        # Level 2: Rule-based response
        try:
            return self.rule_based_response(query)
        except Exception:
            pass
        
        # Level 3: Template response
        return f"I encountered an issue processing your request. Please try rephrasing."
    
    def simple_process(self, query: str) -> str:
        """
        Simplified processing for fallback.
        
        To be implemented by subclasses.
        """
        return f"I understand you're asking about: {query}"
    
    def rule_based_response(self, query: str) -> str:
        """
        Rule-based response for fallback.
        
        To be implemented by subclasses.
        """
        return "I can help with that. Let me think about it."
    
    def get_safe_fallback(self, query: str) -> str:
        """
        Safe fallback response.
        """
        return "I'm sorry, I can't process that request right now. Please try again later."
    
    def _store_memory(self, query: str, response: Any) -> None:
        """
        Store interaction in memory systems.
        """
        if not self.memory or not self.episodic:
            return
        
        try:
            # Store in vector memory
            memory_text = f"Q: {query}\nA: {response}"
            self.memory.add(
                text=memory_text,
                metadata={
                    "agent": self.agent_id,
                    "timestamp": datetime.now().isoformat(),
                    "type": "interaction"
                }
            )
            
            # Log in episodic memory
            self.episodic.log(
                agent=self.agent_id,
                event_type="interaction",
                data={
                    "query": query,
                    "response": str(response),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to store memory for {self.name}: {e}")
            raise MemoryError(f"Memory storage failed: {e}")
    
    def _create_success_response(self, result: Any) -> Dict[str, Any]:
        """Create standardized success response."""
        return {
            'success': True,
            'result': result,
            'agent': self.name,
            'error': None,
            'error_type': None,
            'fallback': None
        }
    
    def _create_error_response(self, error: str, error_type: str, 
                              fallback: Optional[str] = None) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            'success': False,
            'result': None,
            'agent': self.name,
            'error': error,
            'error_type': error_type,
            'fallback': fallback or self.get_safe_fallback(error)
        }
    
    def register_with_orchestrator(self, orchestrator):
        """
        Register this agent with the orchestrator.
        
        Args:
            orchestrator: The orchestrator instance
        """
        self.orchestrator = orchestrator
        logger.info(f"Agent {self.name} registered with orchestrator")
    
    def notify_error(self, error: Exception, context: dict):
        """
        Notify orchestrator of critical errors.
        """
        if self.episodic:
            self.episodic.log(
                agent=self.name,
                event_type="error",
                data={
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "context": context,
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        if self.orchestrator:
            self.orchestrator.log_error(self.name, error, context)
    
    def get_recent_memories(self, limit: int = 5) -> List[str]:
        """
        Get recent memories related to this agent.
        """
        if not self.memory:
            return []
        
        try:
            # This is a simplified approach - in practice, you'd want
            # to search for relevant memories based on current context
            recent = self.memory.search("recent interactions", limit=limit)
            return [memory['text'] for memory in recent] if recent else []
        except Exception as e:
            logger.error(f"Failed to get recent memories: {e}")
            return []
    
    def get_recent_events(self, limit: int = 10) -> List[dict]:
        """
        Get recent episodic events for this agent.
        """
        if not self.episodic:
            return []
        
        try:
            return self.episodic.get_recent(agent=self.agent_id, limit=limit)
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []


# Example usage and testing
if __name__ == "__main__":
    # Test the base class
    class TestAgent(BaseSpecializedAgent):
        def process(self, query: str, context: Dict[str, Any]) -> str:
            return f"Processed: {query}"
    
    # Initialize
    agent = TestAgent("test_agent")
    
    # Test handle method
    response = agent.handle("Hello, how are you?")
    print("Test response:", response)
    
    # Test error handling
    class BrokenAgent(BaseSpecializedAgent):
        def process(self, query: str, context: Dict[str, Any]) -> str:
            raise ProcessingError("Test error")
    
    broken = BrokenAgent("broken_agent")
    error_response = broken.handle("This will fail")
    print("Error response:", error_response)
