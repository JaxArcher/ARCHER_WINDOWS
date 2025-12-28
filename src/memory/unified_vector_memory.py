"""
Unified Vector Memory System for ARCHER

Combines ChromaDB (local) and Pinecone (cloud) for scalable, cross-agent memory sharing.
Provides semantic search, embedding storage, and memory consolidation.
"""

import os
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger(__name__)


def redact_pii(text: str) -> str:
    """
    Redact personally identifiable information from text.
    """
    import re

    pii_patterns = {
        r"\b\d{3}-\d{2}-\d{4}\b": "[REDACTED_SSN]",
        r"\b\d{4} \d{4} \d{4} \d{4}\b": "[REDACTED_CARD]",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b": "[REDACTED_EMAIL]",
        r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b": "[REDACTED_PHONE]",
        r"\b\d{1,5}\s\w+\s\w+\b": "[REDACTED_ADDRESS]",
        r"\b(?:sk-|pk_|api_key|apikey|token|secret)[a-zA-Z0-9_-]{20,}\b": "[REDACTED_API_KEY]",
        r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b": "[REDACTED_IPV4]",
        r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b": "[REDACTED_IPV6]",
        r"/home/[^/\s]+(?:/[^/\s]*)*": "[REDACTED_USER_PATH_UNIX]",
        r"C:\\Users\\[^\\]+(?:\\[^\\]*)*": "[REDACTED_USER_PATH_WIN]",
    }

    redacted = text
    for pattern, replacement in pii_patterns.items():
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)

    return redacted


try:
    import chromadb
    from chromadb.config import Settings

    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logger.warning("ChromaDB not available. Install with: pip install chromadb")

try:
    from pinecone import Pinecone, ServerlessSpec

    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.warning("Pinecone not available. Install with: pip install pinecone-client")

try:
    import sentence_transformers
    from sentence_transformers import SentenceTransformer

    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    logger.warning(
        "Sentence transformers not available. Install with: pip install sentence-transformers"
    )


class UnifiedVectorMemory:
    """
    Unified vector memory system combining local ChromaDB and cloud Pinecone.

    Features:
    - Dual storage: Local ChromaDB + Cloud Pinecone
    - Automatic failover and sync
    - Cross-agent memory sharing
    - Semantic search with embeddings
    - Memory consolidation and cleanup
    """

    def __init__(
        self,
        collection_name: str = "archer_memory",
        embedding_model: str = "all-MiniLM-L6-v2",
        use_pinecone: bool = True,
        use_chroma: bool = True,
    ):
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.use_pinecone = use_pinecone and PINECONE_AVAILABLE
        self.use_chroma = use_chroma and CHROMA_AVAILABLE

        # Initialize embedding model
        self.embedding_model = None
        if EMBEDDING_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
                logger.info(f"Loaded embedding model: {embedding_model}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")

        # Initialize ChromaDB (local)
        self.chroma_client = None
        self.chroma_collection = None
        if self.use_chroma:
            try:
                self.chroma_client = chromadb.PersistentClient(
                    path="./data/chroma_db",
                    settings=Settings(anonymized_telemetry=False),
                )
                self.chroma_collection = self.chroma_client.get_or_create_collection(
                    name=collection_name,
                    metadata={"description": "ARCHER unified memory"},
                )
                logger.info("ChromaDB initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {e}")
                self.use_chroma = False

        # Initialize Pinecone (cloud)
        self.pinecone_client = None
        self.pinecone_index = None
        if self.use_pinecone:
            try:
                api_key = os.getenv("PINECONE_API_KEY")
                if not api_key:
                    logger.warning("PINECONE_API_KEY not set, disabling Pinecone")
                    self.use_pinecone = False
                else:
                    self.pinecone_client = Pinecone(api_key=api_key)

                    # Create index if it doesn't exist
                    index_name = f"{collection_name.replace('_', '-')}"
                    if index_name not in self.pinecone_client.list_indexes().names():
                        self.pinecone_client.create_index(
                            name=index_name,
                            dimension=384,  # all-MiniLM-L6-v2 dimension
                            metric="cosine",
                            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                        )
                        logger.info(f"Created Pinecone index: {index_name}")

                    self.pinecone_index = self.pinecone_client.Index(index_name)
                    logger.info("Pinecone initialized successfully")

            except Exception as e:
                logger.error(f"Failed to initialize Pinecone: {e}")
                self.use_pinecone = False

        # Memory statistics
        self.stats = {
            "total_memories": 0,
            "chroma_memories": 0,
            "pinecone_memories": 0,
            "last_sync": None,
        }

        logger.info(
            f"Unified Vector Memory initialized - ChromaDB: {self.use_chroma}, Pinecone: {self.use_pinecone}"
        )

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if not self.embedding_model:
            # Fallback: simple hash-based embedding (not recommended for production)
            hash_obj = hashlib.md5(text.encode())
            hash_bytes = hash_obj.digest()
            return [float(b) / 255.0 for b in hash_bytes] * 16  # 256-dim fallback

        try:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return [0.0] * 384  # Default dimension

    def store_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: str = "unknown",
        memory_type: str = "general",
    ) -> str:
        """
        Store a memory in the vector database.

        Args:
            content: The memory content to store
            metadata: Additional metadata
            agent_id: ID of the agent storing the memory
            memory_type: Type of memory (conversation, observation, etc.)

        Returns:
            Memory ID
        """
        if not content.strip():
            return ""

        # Redact PII from content
        content = redact_pii(content)

        # Generate unique ID
        timestamp = int(time.time() * 1000000)  # Microsecond precision
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        memory_id = f"{agent_id}_{memory_type}_{timestamp}_{content_hash}"

        # Prepare metadata
        full_metadata = {
            "agent_id": agent_id,
            "memory_type": memory_type,
            "timestamp": timestamp,
            "content_length": len(content),
            "created_at": datetime.now().isoformat(),
        }
        if metadata:
            full_metadata.update(metadata)

        # Generate embedding
        embedding = self._generate_embedding(content)

        # Store in ChromaDB
        if self.use_chroma:
            try:
                self.chroma_collection.add(
                    ids=[memory_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[full_metadata],
                )
                self.stats["chroma_memories"] += 1
                logger.debug(f"Stored memory in ChromaDB: {memory_id}")
            except Exception as e:
                logger.error(f"ChromaDB storage failed: {e}")

        # Store in Pinecone
        if self.use_pinecone:
            try:
                self.pinecone_index.upsert(
                    vectors=[
                        {
                            "id": memory_id,
                            "values": embedding,
                            "metadata": {
                                k: str(v) for k, v in full_metadata.items()
                            },  # Pinecone requires string metadata
                        }
                    ]
                )
                self.stats["pinecone_memories"] += 1
                logger.debug(f"Stored memory in Pinecone: {memory_id}")
            except Exception as e:
                logger.error(f"Pinecone storage failed: {e}")

        self.stats["total_memories"] += 1
        return memory_id

    def search_memories(
        self,
        query: str,
        limit: int = 10,
        agent_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        use_pinecone: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search memories by semantic similarity.

        Args:
            query: Search query
            limit: Maximum results to return
            agent_filter: Filter by agent ID
            type_filter: Filter by memory type
            use_pinecone: Prefer Pinecone over ChromaDB

        Returns:
            List of matching memories with scores
        """
        if not query.strip():
            return []

        query_embedding = self._generate_embedding(query)

        results = []

        # Try Pinecone first (if enabled and preferred)
        if use_pinecone and self.use_pinecone:
            try:
                # Prepare filter
                filter_dict = {}
                if agent_filter:
                    filter_dict["agent_id"] = agent_filter
                if type_filter:
                    filter_dict["memory_type"] = type_filter

                pinecone_results = self.pinecone_index.query(
                    vector=query_embedding,
                    top_k=limit,
                    include_metadata=True,
                    filter=filter_dict if filter_dict else None,
                )

                for match in pinecone_results["matches"]:
                    results.append(
                        {
                            "id": match["id"],
                            "content": match["metadata"].get("content", ""),
                            "score": match["score"],
                            "metadata": match["metadata"],
                            "source": "pinecone",
                        }
                    )

                if results:
                    logger.debug(f"Pinecone search returned {len(results)} results")
                    return results

            except Exception as e:
                logger.error(f"Pinecone search failed: {e}")

        # Fallback to ChromaDB
        if self.use_chroma:
            try:
                # Prepare where clause
                where_clause = {}
                if agent_filter:
                    where_clause["agent_id"] = agent_filter
                if type_filter:
                    where_clause["memory_type"] = type_filter

                chroma_results = self.chroma_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    where=where_clause if where_clause else None,
                    include=["documents", "metadatas", "distances"],
                )

                for i, doc in enumerate(chroma_results["documents"][0]):
                    distance = chroma_results["distances"][0][i]
                    metadata = chroma_results["metadatas"][0][i]

                    results.append(
                        {
                            "id": chroma_results["ids"][0][i],
                            "content": doc,
                            "score": 1.0 - distance,  # Convert distance to similarity
                            "metadata": metadata,
                            "source": "chroma",
                        }
                    )

                logger.debug(f"ChromaDB search returned {len(results)} results")

            except Exception as e:
                logger.error(f"ChromaDB search failed: {e}")

        return results

    def get_memory_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific memory by ID."""
        # Try ChromaDB first
        if self.use_chroma:
            try:
                result = self.chroma_collection.get(ids=[memory_id])
                if result["documents"]:
                    return {
                        "id": memory_id,
                        "content": result["documents"][0],
                        "metadata": result["metadatas"][0],
                        "source": "chroma",
                    }
            except Exception as e:
                logger.debug(f"ChromaDB get failed: {e}")

        # Try Pinecone
        if self.use_pinecone:
            try:
                result = self.pinecone_index.fetch(ids=[memory_id])
                if result["vectors"]:
                    vector_data = result["vectors"][memory_id]
                    return {
                        "id": memory_id,
                        "content": "",  # Pinecone doesn't store content in metadata
                        "metadata": vector_data["metadata"],
                        "source": "pinecone",
                    }
            except Exception as e:
                logger.debug(f"Pinecone get failed: {e}")

        return None

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        success = False

        # Delete from ChromaDB
        if self.use_chroma:
            try:
                self.chroma_collection.delete(ids=[memory_id])
                self.stats["chroma_memories"] = max(
                    0, self.stats["chroma_memories"] - 1
                )
                success = True
            except Exception as e:
                logger.error(f"ChromaDB delete failed: {e}")

        # Delete from Pinecone
        if self.use_pinecone:
            try:
                self.pinecone_index.delete(ids=[memory_id])
                self.stats["pinecone_memories"] = max(
                    0, self.stats["pinecone_memories"] - 1
                )
                success = True
            except Exception as e:
                logger.error(f"Pinecone delete failed: {e}")

        if success:
            self.stats["total_memories"] = max(0, self.stats["total_memories"] - 1)

        return success

    def consolidate_memories(self, days_to_keep: int = 90):
        """Consolidate and clean up old memories."""
        cutoff_timestamp = int(
            (datetime.now() - timedelta(days=days_to_keep)).timestamp() * 1000000
        )

        logger.info(f"Starting memory consolidation, keeping last {days_to_keep} days")

        # ChromaDB cleanup
        if self.use_chroma:
            try:
                # Get all memories with timestamps
                results = self.chroma_collection.get(include=["metadatas"])
                old_ids = []

                for i, metadata in enumerate(results["metadatas"]):
                    timestamp = metadata.get("timestamp", 0)
                    if timestamp < cutoff_timestamp:
                        old_ids.append(results["ids"][i])

                if old_ids:
                    self.chroma_collection.delete(ids=old_ids)
                    logger.info(f"Deleted {len(old_ids)} old memories from ChromaDB")

            except Exception as e:
                logger.error(f"ChromaDB consolidation failed: {e}")

        # Pinecone cleanup (would require more complex filtering)
        # For now, just log that consolidation occurred
        self.stats["last_sync"] = datetime.now().isoformat()
        logger.info("Memory consolidation completed")

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return {
            **self.stats,
            "chroma_available": self.use_chroma,
            "pinecone_available": self.use_pinecone,
            "embedding_model": self.embedding_model_name
            if self.embedding_model
            else None,
        }

    def sync_memories(self):
        """Sync memories between ChromaDB and Pinecone."""
        if not (self.use_chroma and self.use_pinecone):
            logger.warning("Both ChromaDB and Pinecone required for sync")
            return

        logger.info("Starting memory synchronization...")

        try:
            # Get all ChromaDB memories
            chroma_results = self.chroma_collection.get(
                include=["embeddings", "documents", "metadatas"]
            )

            # Sync to Pinecone
            vectors_to_sync = []
            for i, memory_id in enumerate(chroma_results["ids"]):
                embedding = chroma_results["embeddings"][i]
                metadata = chroma_results["metadatas"][i]

                # Convert metadata to strings for Pinecone
                string_metadata = {k: str(v) for k, v in metadata.items()}

                vectors_to_sync.append(
                    {"id": memory_id, "values": embedding, "metadata": string_metadata}
                )

            if vectors_to_sync:
                # Batch upsert to Pinecone
                batch_size = 100
                for i in range(0, len(vectors_to_sync), batch_size):
                    batch = vectors_to_sync[i : i + batch_size]
                    self.pinecone_index.upsert(vectors=batch)

                logger.info(f"Synced {len(vectors_to_sync)} memories to Pinecone")

            self.stats["last_sync"] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"Memory sync failed: {e}")

    def get_context_for_agent(
        self, agent_id: str, query: str = "", limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get relevant context memories for an agent.

        Args:
            agent_id: The agent requesting context
            query: Optional query to search for relevant memories
            limit: Maximum memories to return

        Returns:
            List of relevant memories
        """
        if query:
            # Search for relevant memories
            memories = self.search_memories(query, limit=limit, agent_filter=agent_id)
        else:
            # Get recent memories for this agent
            # Note: This is a simplified version - in practice you'd want time-based filtering
            memories = self.search_memories(f"agent:{agent_id}", limit=limit)

        return memories


# Global instance
_memory_instance = None


def get_unified_memory() -> UnifiedVectorMemory:
    """Get the global unified memory instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = UnifiedVectorMemory()
    return _memory_instance


def store_shared_memory(
    content: str,
    agent_id: str,
    memory_type: str = "general",
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Convenience function to store memory in the unified system."""
    return get_unified_memory().store_memory(content, metadata, agent_id, memory_type)


def search_shared_memory(
    query: str, agent_id: Optional[str] = None, limit: int = 10
) -> List[Dict[str, Any]]:
    """Convenience function to search memories in the unified system."""
    return get_unified_memory().search_memories(query, limit, agent_filter=agent_id)
