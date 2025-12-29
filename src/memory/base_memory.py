"""
Base Memory API for ARCHER

Unified interface for the 4-tier memory system.
Provides standardized methods for all memory types and coordinates
cross-agent memory access.

Features:
- Unified API for all memory tiers
- Standardized methods: add(), retrieve(), search()
- Memory consolidation across tiers
- Cross-agent memory sharing
- Performance monitoring
"""

import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class MemoryError(Exception):
    """Base exception for memory errors."""
    pass


class MemoryAPI:
    """
    Unified memory API that coordinates all 4 tiers of memory.
    """
    
    def __init__(self):
        """Initialize the unified memory API."""
        
        # Initialize all memory tiers
        self.short_term = None  # Tier 1: Short-term memory (context window)
        self.long_term = None   # Tier 2: Long-term vector memory
        self.episodic = None    # Tier 3: Episodic memory
        self.semantic = None    # Tier 4: Semantic memory
        
        # Performance metrics
        self.performance = {
            "total_operations": 0,
            "operation_times": [],
            "last_consolidation": None
        }
        
        # Initialize memory systems
        self._initialize_memory_systems()
        
        logger.info("MemoryAPI initialized")
    
    def _initialize_memory_systems(self):
        """Initialize all memory systems."""
        
        try:
            # Tier 1: Short-term memory (simple in-memory buffer)
            self.short_term = {
                "max_size": 100,
                "items": [],
                "current_size": 0
            }
            logger.info("Short-term memory initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize short-term memory: {e}")
        
        try:
            # Tier 2: Long-term vector memory
            from src.memory.long_term import VectorMemory
            self.long_term = VectorMemory(collection_name="global_memory")
            logger.info("Long-term vector memory initialized")
            
        except Exception as e:
            logger.warning(f"Long-term memory initialization failed: {e}")
        
        try:
            # Tier 3: Episodic memory
            from src.memory.episodic_memory import EpisodicMemory
            self.episodic = EpisodicMemory()
            logger.info("Episodic memory initialized")
            
        except Exception as e:
            logger.warning(f"Episodic memory initialization failed: {e}")
        
        try:
            # Tier 4: Semantic memory
            from src.memory.semantic_memory import SemanticMemory
            self.semantic = SemanticMemory()
            logger.info("Semantic memory initialized")
            
        except Exception as e:
            logger.warning(f"Semantic memory initialization failed: {e}")
    
    def add(self, text: str, metadata: Optional[Dict[str, Any]] = None, 
            memory_type: str = "general", agent_id: Optional[str] = None) -> str:
        """
        Add memory to all appropriate tiers.
        
        Args:
            text: Memory content
            metadata: Additional metadata
            memory_type: Type of memory (interaction, observation, etc.)
            agent_id: ID of the agent adding the memory
            
        Returns:
            Memory ID from long-term storage
            
        Raises:
            MemoryError: If memory addition fails
        """
        
        start_time = time.time()
        self.performance["total_operations"] += 1
        
        if not text or not text.strip():
            raise MemoryError("Memory text cannot be empty")
        
        memory_id = None
        
        try:
            # Add to short-term memory (Tier 1)
            self._add_to_short_term(text, metadata, memory_type, agent_id)
            
            # Add to long-term memory (Tier 2)
            if self.long_term:
                memory_id = self.long_term.add(text, metadata)
            
            # Log to episodic memory (Tier 3)
            if self.episodic:
                self.episodic.store_event(
                    event_type=memory_type,
                    data={"text": text, "metadata": metadata or {}},
                    metadata={"agent": agent_id, "source": "memory_api"}
                )
            
            # Update semantic memory (Tier 4) if relevant
            if self.semantic and memory_type in ["interaction", "learning", "preference"]:
                # Extract key information and store in semantic memory
                self._update_semantic_memory(text, metadata, agent_id)
            
            # Record operation time
            operation_time = time.time() - start_time
            self.performance["operation_times"].append(operation_time)
            
            logger.debug(f"Memory added to all tiers: {memory_id}")
            
            return memory_id or f"mem_{int(time.time() * 1000)}"
            
        except Exception as e:
            logger.error(f"Memory addition failed: {e}")
            raise MemoryError(f"Failed to add memory: {e}")
    
    def _add_to_short_term(self, text: str, metadata: Dict[str, Any], 
                          memory_type: str, agent_id: Optional[str]):
        """Add memory to short-term buffer."""
        
        if not self.short_term:
            return
        
        memory_item = {
            "timestamp": time.time(),
            "text": text,
            "metadata": metadata or {},
            "memory_type": memory_type,
            "agent_id": agent_id,
            "source": "short_term"
        }
        
        # Add to buffer
        self.short_term["items"].append(memory_item)
        self.short_term["current_size"] += 1
        
        # Enforce size limit
        if self.short_term["current_size"] > self.short_term["max_size"]:
            self.short_term["items"].pop(0)
            self.short_term["current_size"] -= 1
    
    def _update_semantic_memory(self, text: str, metadata: Dict[str, Any], 
                               agent_id: Optional[str]):
        """Update semantic memory with relevant information."""
        
        if not self.semantic:
            return
        
        try:
            # Simple topic extraction
            topics = self._extract_topics(text)
            
            for topic in topics:
                self.semantic.store_fact(
                    category="user_profile",
                    key=f"interests.{topic}",
                    value=True
                )
            
            # Record interaction
            if topics:
                self.semantic.record_interaction(topics[0])
                
        except Exception as e:
            logger.warning(f"Failed to update semantic memory: {e}")
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text (simple keyword-based)."""
        
        topic_keywords = {
            "health": ["health", "wellness", "medical", "therapy"],
            "finance": ["stock", "investment", "money", "market"],
            "learning": ["learn", "study", "education", "skill"],
            "technology": ["tech", "computer", "software", "ai"],
            "general": ["help", "assist", "support", "question"]
        }
        
        text_lower = text.lower()
        found_topics = []
        
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in text_lower and topic not in found_topics:
                    found_topics.append(topic)
                    break
        
        return found_topics if found_topics else ["general"]
    
    def search(self, query: str, limit: int = 10, 
               agent_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search across all memory tiers.
        
        Args:
            query: Search query
            limit: Maximum results to return
            agent_filter: Filter by agent ID
            
        Returns:
            List of matching memories with scores and source information
        """
        
        start_time = time.time()
        self.performance["total_operations"] += 1
        
        results = []
        
        try:
            # Search short-term memory
            short_term_results = self._search_short_term(query, limit)
            results.extend(short_term_results)
            
            # Search long-term memory
            if self.long_term:
                long_term_results = self.long_term.search(query, limit)
                # Add source information
                for result in long_term_results:
                    result["source"] = "long_term"
                results.extend(long_term_results)
            
            # Search episodic memory
            if self.episodic:
                episodic_results = self._search_episodic(query, limit)
                results.extend(episodic_results)
            
            # Sort by score (descending)
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            # Apply limit
            results = results[:limit]
            
            # Record operation time
            operation_time = time.time() - start_time
            self.performance["operation_times"].append(operation_time)
            
            logger.debug(f"Memory search returned {len(results)} results")
            
            return results
            
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            raise MemoryError(f"Search failed: {e}")
    
    def _search_short_term(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search short-term memory."""
        
        if not self.short_term or not self.short_term["items"]:
            return []
        
        query_lower = query.lower()
        results = []
        
        # Simple text search in short-term memory
        for item in reversed(self.short_term["items"]):  # Search recent first
            if query_lower in item["text"].lower():
                results.append({
                    "id": f"short_{len(results)}",
                    "content": item["text"],
                    "score": 0.9,  # High score for recent items
                    "metadata": item["metadata"],
                    "source": "short_term",
                    "timestamp": item["timestamp"]
                })
                
                if len(results) >= limit:
                    break
        
        return results
    
    def _search_episodic(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search episodic memory."""
        
        if not self.episodic:
            return []
        
        try:
            events = self.episodic.search_events(query, limit=limit)
            
            results = []
            for event in events:
                results.append({
                    "id": event.get("event_id", "epi_" + str(len(results))),
                    "content": json.dumps(event["data"]),
                    "score": 0.7,  # Medium score for episodic events
                    "metadata": event["metadata"],
                    "source": "episodic",
                    "timestamp": event["timestamp"],
                    "event_type": event["event_type"]
                })
            
            return results
            
        except Exception as e:
            logger.warning(f"Episodic search failed: {e}")
            return []
    
    def get_recent(self, limit: int = 10, agent_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent memories across all tiers.
        
        Args:
            limit: Maximum results to return
            agent_filter: Filter by agent ID
            
        Returns:
            List of recent memories
        """
        
        start_time = time.time()
        self.performance["total_operations"] += 1
        
        recent_memories = []
        
        try:
            # Get from short-term memory
            if self.short_term:
                short_term_recent = self.short_term["items"][-limit:]
                for item in short_term_recent:
                    recent_memories.append({
                        "content": item["text"],
                        "source": "short_term",
                        "timestamp": item["timestamp"],
                        "metadata": item["metadata"],
                        "agent_id": item.get("agent_id")
                    })
            
            # Get from episodic memory
            if self.episodic:
                try:
                    recent_events = self.episodic.get_recent_events(hours=24, limit=limit)
                    for event in recent_events:
                        recent_memories.append({
                            "content": json.dumps(event["data"]),
                            "source": "episodic",
                            "timestamp": event["timestamp"],
                            "metadata": event["metadata"],
                            "event_type": event["event_type"]
                        })
                except Exception as e:
                    logger.warning(f"Failed to get recent episodic events: {e}")
            
            # Sort by timestamp (newest first)
            recent_memories.sort(key=lambda x: x["timestamp"], reverse=True)
            recent_memories = recent_memories[:limit]
            
            # Apply agent filter if specified
            if agent_filter:
                recent_memories = [
                    mem for mem in recent_memories 
                    if mem.get("agent_id") == agent_filter or 
                       (mem.get("metadata", {}).get("agent") == agent_filter)
                ]
            
            # Record operation time
            operation_time = time.time() - start_time
            self.performance["operation_times"].append(operation_time)
            
            logger.debug(f"Retrieved {len(recent_memories)} recent memories")
            
            return recent_memories
            
        except Exception as e:
            logger.error(f"Failed to get recent memories: {e}")
            raise MemoryError(f"Failed to retrieve recent memories: {e}")
    
    def consolidate(self):
        """
        Consolidate memories across tiers.
        
        Moves important short-term memories to long-term storage
        and updates semantic memory with patterns.
        """
        
        if not self.long_term or not self.short_term:
            logger.warning("Memory consolidation requires both short-term and long-term memory")
            return False
        
        try:
            start_time = time.time()
            
            # Find important short-term memories to consolidate
            important_memories = []
            
            for item in self.short_term["items"]:
                # Simple heuristic: longer memories are more important
                if len(item["text"]) > 100:  # More than 100 characters
                    important_memories.append(item)
            
            # Add to long-term memory
            for memory in important_memories:
                try:
                    self.long_term.add(
                        memory["text"],
                        metadata={
                            "source": "consolidated",
                            "original_timestamp": memory["timestamp"],
                            "memory_type": memory["memory_type"],
                            "agent_id": memory.get("agent_id")
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to consolidate memory: {e}")
            
            # Update statistics
            consolidation_time = time.time() - start_time
            self.performance["last_consolidation"] = datetime.now().isoformat()
            
            logger.info(f"Memory consolidation completed: {len(important_memories)} memories consolidated in {consolidation_time:.3f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"Memory consolidation failed: {e}")
            return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the memory system.
        
        Returns:
            Dictionary of performance metrics
        """
        
        metrics = self.performance.copy()
        
        if metrics["operation_times"]:
            metrics["avg_operation_time"] = sum(metrics["operation_times"]) / len(metrics["operation_times"])
        else:
            metrics["avg_operation_time"] = 0.0
        
        # Add individual memory system stats
        if self.long_term:
            metrics["long_term_stats"] = self.long_term.get_stats()
        
        return metrics
    
    def reset_short_term(self):
        """Reset short-term memory buffer."""
        
        if self.short_term:
            self.short_term["items"] = []
            self.short_term["current_size"] = 0
            logger.info("Short-term memory reset")
        
        return True
    
    def __repr__(self) -> str:
        """String representation."""
        
        memory_status = {
            "short_term": "enabled" if self.short_term else "disabled",
            "long_term": "enabled" if self.long_term else "disabled",
            "episodic": "enabled" if self.episodic else "disabled",
            "semantic": "enabled" if self.semantic else "disabled"
        }
        
        return f"MemoryAPI({memory_status})"


# Global instance for convenience
def get_memory_api() -> MemoryAPI:
    """
    Get the global memory API instance.
    
    Returns:
        MemoryAPI instance
    """
    global _memory_api_instance
    if not hasattr(get_memory_api, "_memory_api_instance"):
        get_memory_api._memory_api_instance = MemoryAPI()
    return get_memory_api._memory_api_instance


# Test the memory API
if __name__ == "__main__":
    print("Testing MemoryAPI...")
    
    # Create memory API
    memory_api = get_memory_api()
    print(f"Memory API created: {memory_api}")
    
    # Test adding memories
    test_memories = [
        "The user is interested in learning Python programming.",
        "Stock market analysis shows positive trends.",
        "Health and wellness are important topics for the user.",
        "Artificial intelligence technologies are advancing rapidly."
    ]
    
    memory_ids = []
    for i, memory in enumerate(test_memories):
        try:
            mem_id = memory_api.add(
                memory,
                metadata={"source": f"test_{i}", "importance": "high"},
                memory_type="learning",
                agent_id="test_agent"
            )
            memory_ids.append(mem_id)
            print(f"Added memory {i+1}: {mem_id}")
        except Exception as e:
            print(f"Failed to add memory {i+1}: {e}")
    
    # Test searching
    if memory_ids:
        search_queries = [
            "Python programming",
            "stock market",
            "health topics"
        ]
        
        for query in search_queries:
            try:
                results = memory_api.search(query, limit=2)
                print(f"\nSearch for '{query}':")
                for i, result in enumerate(results, 1):
                    print(f"  {i}. Source: {result['source']}, Score: {result['score']:.3f}")
                    print(f"     {result['content'][:60]}...")
            except Exception as e:
                print(f"Search failed for '{query}': {e}")
    
    # Test getting recent memories
    try:
        recent = memory_api.get_recent(limit=3)
        print(f"\nRecent memories ({len(recent)}):")
        for i, mem in enumerate(recent, 1):
            print(f"  {i}. {mem['source']}: {mem['content'][:50]}...")
    except Exception as e:
        print(f"Failed to get recent memories: {e}")
    
    # Test consolidation
    try:
        memory_api.consolidate()
        print("\nMemory consolidation completed")
    except Exception as e:
        print(f"Consolidation failed: {e}")
    
    print(f"\nMemory API performance: {memory_api.get_performance_metrics()}")
    print("MemoryAPI test completed!")