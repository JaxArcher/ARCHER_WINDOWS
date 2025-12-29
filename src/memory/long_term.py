"""
Long-term Vector Memory for ARCHER

ChromaDB-based vector memory system for semantic search and long-term storage.
This implements Tier 2 of the 4-tier memory system.

Features:
- ChromaDB vector storage
- Semantic search with embeddings
- Agent-specific collections
- Memory retrieval by similarity
- Performance monitoring
"""

import logging
import time
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import hashlib

# Configure logging
logger = logging.getLogger(__name__)


class VectorMemoryError(Exception):
    """Base exception for vector memory errors."""
    pass


class VectorMemory:
    """
    Long-term vector memory using ChromaDB for semantic search.
    """
    
    def __init__(self, collection_name: str = "global_memory"):
        """
        Initialize vector memory with ChromaDB.
        
        Args:
            collection_name: Name of the ChromaDB collection
        """
        
        self.collection_name = collection_name
        self.chroma_client = None
        self.collection = None
        self.embedding_model = None
        self.stats = {
            "total_memories": 0,
            "last_access": None,
            "avg_retrieval_time": 0.0
        }
        
        # Initialize ChromaDB
        self._initialize_chroma()
        
        logger.info(f"VectorMemory initialized: {collection_name}")
    
    def _initialize_chroma(self):
        """Initialize ChromaDB client and collection."""
        
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Create persistent ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path="./data/chroma_db",
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": f"ARCHER {self.collection_name} memory"}
            )
            
            logger.info(f"ChromaDB collection '{self.collection_name}' initialized")
            
        except ImportError:
            logger.warning("ChromaDB not available. Install with: pip install chromadb")
            self.chroma_client = None
            self.collection = None
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.chroma_client = None
            self.collection = None
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        
        # Try to use sentence transformers if available
        try:
            from sentence_transformers import SentenceTransformer
            
            if self.embedding_model is None:
                # Load a lightweight model
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Loaded embedding model: all-MiniLM-L6-v2")
            
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
            
        except ImportError:
            logger.warning("Sentence transformers not available, using fallback embedding")
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            
        # Fallback: simple hash-based embedding (not recommended for production)
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        return [float(b) / 255.0 for b in hash_bytes] * 16  # 256-dim fallback
    
    def add(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a memory to the vector database.
        
        Args:
            text: Memory content
            metadata: Additional metadata
            
        Returns:
            Memory ID
            
        Raises:
            VectorMemoryError: If memory addition fails
        """
        
        if not self.collection:
            raise VectorMemoryError("Vector memory not initialized")
            
        if not text or not text.strip():
            raise VectorMemoryError("Memory text cannot be empty")
        
        try:
            # Generate unique ID
            timestamp = int(time.time() * 1000000)  # Microsecond precision
            content_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            memory_id = f"mem_{timestamp}_{content_hash}"
            
            # Generate embedding
            embedding = self._generate_embedding(text)
            
            # Prepare metadata
            full_metadata = {
                "timestamp": datetime.now().isoformat(),
                "content_length": len(text),
                "collection": self.collection_name
            }
            
            if metadata:
                full_metadata.update(metadata)
            
            # Add to ChromaDB
            self.collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[full_metadata]
            )
            
            self.stats["total_memories"] += 1
            self.stats["last_access"] = datetime.now().isoformat()
            
            logger.debug(f"Added memory to vector store: {memory_id}")
            
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise VectorMemoryError(f"Memory addition failed: {e}")
    
    def search(self, query: str, limit: int = 10, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search memories by semantic similarity.
        
        Args:
            query: Search query
            limit: Maximum results to return
            where: Filter conditions
            
        Returns:
            List of matching memories with scores
            
        Raises:
            VectorMemoryError: If search fails
        """
        
        if not self.collection:
            raise VectorMemoryError("Vector memory not initialized")
            
        if not query or not query.strip():
            return []
        
        start_time = time.time()
        
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            
            # Perform search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            # Process results
            memories = []
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i]
                metadata = results["metadatas"][0][i]
                
                memories.append({
                    "id": results["ids"][0][i],
                    "content": doc,
                    "score": 1.0 - distance,  # Convert distance to similarity score
                    "metadata": metadata,
                    "distance": distance
                })
            
            # Update statistics
            retrieval_time = time.time() - start_time
            if self.stats["total_memories"] > 0:
                self.stats["avg_retrieval_time"] = (
                    self.stats["avg_retrieval_time"] * 0.9 + retrieval_time * 0.1
                )
            else:
                self.stats["avg_retrieval_time"] = retrieval_time
                
            self.stats["last_access"] = datetime.now().isoformat()
            
            logger.debug(f"Vector search returned {len(memories)} results in {retrieval_time:.3f}s")
            
            return memories
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise VectorMemoryError(f"Search failed: {e}")
    
    def get_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific memory by ID.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Memory data or None if not found
        """
        
        if not self.collection:
            return None
            
        try:
            result = self.collection.get(ids=[memory_id])
            
            if result["documents"]:
                return {
                    "id": memory_id,
                    "content": result["documents"][0],
                    "metadata": result["metadatas"][0]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get memory by ID: {e}")
            return None
    
    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.
        
        Args:
            memory_id: Memory ID to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        
        if not self.collection:
            return False
            
        try:
            self.collection.delete(ids=[memory_id])
            self.stats["total_memories"] = max(0, self.stats["total_memories"] - 1)
            logger.debug(f"Deleted memory: {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics.
        
        Returns:
            Dictionary of statistics
        """
        
        stats = self.stats.copy()
        
        if self.collection:
            try:
                collection_info = self.chroma_client.get_collection(self.collection_name)
                stats["chroma_collection_size"] = collection_info.count()
            except Exception:
                pass
        
        return stats
    
    def __len__(self) -> int:
        """Return number of stored memories."""
        return self.stats["total_memories"]
    
    def __repr__(self) -> str:
        """String representation."""
        return f"VectorMemory(collection='{self.collection_name}', memories={len(self)})"


# Global instance for convenience
def get_vector_memory(collection_name: str = "global_memory") -> VectorMemory:
    """
    Get a vector memory instance.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        VectorMemory instance
    """
    return VectorMemory(collection_name)


# Test the vector memory
if __name__ == "__main__":
    print("Testing VectorMemory...")
    
    # Create vector memory
    vm = get_vector_memory("test_collection")
    print(f"Vector memory created: {vm}")
    
    # Test adding memories
    test_memories = [
        "The stock market is performing well today.",
        "Python programming is a valuable skill to learn.",
        "Health and wellness are important for productivity.",
        "Artificial intelligence is transforming industries."
    ]
    
    memory_ids = []
    for i, memory in enumerate(test_memories):
        try:
            mem_id = vm.add(memory, metadata={"source": f"test_{i}", "category": "general"})
            memory_ids.append(mem_id)
            print(f"Added memory {i+1}: {mem_id}")
        except Exception as e:
            print(f"Failed to add memory {i+1}: {e}")
    
    # Test searching
    if memory_ids:
        search_queries = [
            "What's happening with stocks?",
            "Tell me about programming",
            "How can I improve my health?"
        ]
        
        for query in search_queries:
            try:
                results = vm.search(query, limit=2)
                print(f"\nSearch for '{query}':")
                for i, result in enumerate(results, 1):
                    print(f"  {i}. Score: {result['score']:.3f} - {result['content'][:50]}...")
            except Exception as e:
                print(f"Search failed for '{query}': {e}")
    
    print(f"\nVector memory stats: {vm.get_stats()}")
    print("VectorMemory test completed!")