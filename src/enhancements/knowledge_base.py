"""
Knowledge Base and RAG System

Implements document ingestion, vector embedding, and retrieval-augmented generation
for ARCHER's knowledge base.
"""

import os
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import json

# Import external libraries
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
from langdetect import detect, DetectorFactory
from textblob import TextBlob
import assemblyai as aai

# Import ARCHER modules
from src.memory.unified_vector_memory import UnifiedVectorMemory

logger = logging.getLogger(__name__)


@dataclass
class DocumentMetadata:
    """Metadata for ingested documents."""
    file_name: str
    file_type: str
    file_size: int
    ingestion_time: str
    source: str = "local"
    language: str = "unknown"
    author: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class KnowledgeChunk:
    """A chunk of knowledge with embeddings."""
    content: str
    embedding: List[float]
    metadata: DocumentMetadata
    chunk_id: str
    document_id: str


class KnowledgeBaseRAG:
    """Knowledge Base with RAG capabilities."""
    
    def __init__(self, collection_name: str = "archer_knowledge_base"):
        self.collection_name = collection_name
        self.chroma_client = chromadb.PersistentClient(path="data/chroma_db")
        self.collection = self._get_or_create_collection()
        
        # Load embedding model
        self.embedding_model = self._load_embedding_model()
        
        # Initialize text processing
        DetectorFactory.seed = 0  # For consistent language detection
        
        logger.info(f"KnowledgeBaseRAG initialized with collection: {collection_name}")
    
    def _get_or_create_collection(self):
        """Get or create the ChromaDB collection."""
        try:
            # Check if collection exists
            collections = self.chroma_client.list_collections()
            collection_names = [col.name for col in collections]
            
            if self.collection_name in collection_names:
                logger.info(f"Loading existing collection: {self.collection_name}")
                return self.chroma_client.get_collection(self.collection_name)
            else:
                logger.info(f"Creating new collection: {self.collection_name}")
                return self.chroma_client.create_collection(self.collection_name)
        except Exception as e:
            logger.error(f"Failed to get/create collection: {e}")
            raise
    
    def _load_embedding_model(self):
        """Load the sentence transformer embedding model."""
        try:
            # Use a smaller model for efficiency
            model_name = "all-MiniLM-L6-v2"
            logger.info(f"Loading embedding model: {model_name}")
            
            # Use ChromaDB's built-in embedding function
            embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model_name
            )
            
            return embedding_func
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def _generate_document_id(self, file_path: str) -> str:
        """Generate a unique document ID from file path."""
        return hashlib.md5(file_path.encode()).hexdigest()
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate a unique chunk ID."""
        return f"{document_id}_chunk_{chunk_index}"
    
    def _extract_text_from_file(self, file_path: str) -> Tuple[str, str]:
        """Extract text from various file types."""
        file_path = Path(file_path)
        
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            file_type = file_path.suffix.lower()
            
            if file_type in ['.txt', '.md', '.csv']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read(), file_type
            elif file_type == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return json.dumps(data, indent=2), file_type
            elif file_type in ['.pdf', '.docx', '.pptx']:
                # For these formats, we'd need additional libraries
                # For now, return a placeholder
                return f"[Document content from {file_path.name}]", file_type
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
                
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            raise
    
    def _chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """Split text into chunks with overlap."""
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            chunks.append(chunk)
            
            # Move start forward by chunk_size - overlap
            start = start + chunk_size - overlap
        
        return chunks
    
    def _detect_language(self, text: str) -> str:
        """Detect the language of text."""
        try:
            if len(text.strip()) == 0:
                return "unknown"
            return detect(text)
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return "unknown"
    
    def _analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze text for metadata and insights."""
        analysis = {
            "language": self._detect_language(text),
            "word_count": len(text.split()),
            "character_count": len(text),
            "sentiment": None,
            "keywords": []
        }
        
        try:
            # Sentiment analysis
            blob = TextBlob(text)
            analysis["sentiment"] = {
                "polarity": blob.sentiment.polarity,
                "subjectivity": blob.sentiment.subjectivity
            }
            
            # Keywords (simple approach)
            words = text.lower().split()
            # Filter out common words and get top 5 unique words
            common_words = {'the', 'and', 'a', 'an', 'in', 'on', 'at', 'to', 'of', 'for', 'is', 'are', 'was', 'were'}
            keywords = [word for word in words if word not in common_words and len(word) > 3]
            analysis["keywords"] = list(set(keywords))[:5]
            
        except Exception as e:
            logger.warning(f"Text analysis failed: {e}")
        
        return analysis
    
    def ingest_document(self, file_path: str, source: str = "local", 
                      metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Ingest a document into the knowledge base."""
        try:
            file_path = Path(file_path)
            
            # Extract text from file
            text, file_type = self._extract_text_from_file(file_path)
            
            # Generate document ID
            document_id = self._generate_document_id(str(file_path))
            
            # Create metadata
            doc_metadata = DocumentMetadata(
                file_name=file_path.name,
                file_type=file_type,
                file_size=file_path.stat().st_size,
                ingestion_time=Path().cwd().name,  # Simple timestamp
                source=source,
                language=self._detect_language(text)
            )
            
            # Add custom metadata if provided
            if metadata:
                for key, value in metadata.items():
                    if hasattr(doc_metadata, key):
                        setattr(doc_metadata, key, value)
            
            # Chunk the text
            chunks = self._chunk_text(text)
            
            # Process each chunk
            chunk_results = []
            
            for i, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
                
                # Generate chunk ID
                chunk_id = self._generate_chunk_id(document_id, i)
                
                # Generate embedding
                embedding = self.embedding_model([chunk])[0]
                
                # Create knowledge chunk
                knowledge_chunk = KnowledgeChunk(
                    content=chunk,
                    embedding=embedding,
                    metadata=doc_metadata,
                    chunk_id=chunk_id,
                    document_id=document_id
                )
                
                # Store in ChromaDB
                self.collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[{
                        "document_id": document_id,
                        "file_name": doc_metadata.file_name,
                        "source": doc_metadata.source,
                        "language": doc_metadata.language,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }]
                )
                
                chunk_results.append({
                    "chunk_id": chunk_id,
                    "content_length": len(chunk),
                    "embedding_length": len(embedding)
                })
            
            logger.info(f"Ingested document {file_path.name}: {len(chunks)} chunks, {len(text)} characters")
            
            return {
                "document_id": document_id,
                "file_name": file_path.name,
                "chunks": len(chunks),
                "total_characters": len(text),
                "language": doc_metadata.language,
                "chunk_details": chunk_results
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest document {file_path}: {e}")
            raise
    
    def ingest_text(self, text: str, source: str = "api", 
                   metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Ingest raw text into the knowledge base."""
        try:
            if not text or not text.strip():
                raise ValueError("Text cannot be empty")
            
            # Generate document ID from text hash
            document_id = self._generate_document_id(text[:100])
            
            # Create metadata
            doc_metadata = DocumentMetadata(
                file_name=f"text_{document_id[:8]}.txt",
                file_type="text",
                file_size=len(text.encode('utf-8')),
                ingestion_time=Path().cwd().name,
                source=source,
                language=self._detect_language(text)
            )
            
            # Add custom metadata if provided
            if metadata:
                for key, value in metadata.items():
                    if hasattr(doc_metadata, key):
                        setattr(doc_metadata, key, value)
            
            # Chunk the text
            chunks = self._chunk_text(text)
            
            # Process each chunk
            chunk_results = []
            
            for i, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
                
                # Generate chunk ID
                chunk_id = self._generate_chunk_id(document_id, i)
                
                # Generate embedding
                embedding = self.embedding_model([chunk])[0]
                
                # Store in ChromaDB
                self.collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[{
                        "document_id": document_id,
                        "file_name": doc_metadata.file_name,
                        "source": doc_metadata.source,
                        "language": doc_metadata.language,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }]
                )
                
                chunk_results.append({
                    "chunk_id": chunk_id,
                    "content_length": len(chunk),
                    "embedding_length": len(embedding)
                })
            
            logger.info(f"Ingested text: {len(chunks)} chunks, {len(text)} characters")
            
            return {
                "document_id": document_id,
                "chunks": len(chunks),
                "total_characters": len(text),
                "language": doc_metadata.language,
                "chunk_details": chunk_results
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest text: {e}")
            raise
    
    def retrieve_relevant_knowledge(self, query: str, top_k: int = 5, 
                                   filters: Optional[Dict] = None) -> List[KnowledgeChunk]:
        """Retrieve knowledge relevant to a query."""
        try:
            if not query or not query.strip():
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_model([query])[0]
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filters or {}
            )
            
            # Process results
            knowledge_chunks = []
            
            for i in range(len(results['ids'][0])):
                chunk_id = results['ids'][0][i]
                content = results['documents'][0][i]
                embedding = results['embeddings'][0][i]
                metadata = results['metadatas'][0][i]
                
                # Create knowledge chunk
                doc_metadata = DocumentMetadata(
                    file_name=metadata.get('file_name', 'unknown'),
                    file_type=metadata.get('file_type', 'text'),
                    file_size=metadata.get('file_size', 0),
                    ingestion_time=metadata.get('ingestion_time', 'unknown'),
                    source=metadata.get('source', 'unknown'),
                    language=metadata.get('language', 'unknown')
                )
                
                knowledge_chunk = KnowledgeChunk(
                    content=content,
                    embedding=embedding,
                    metadata=doc_metadata,
                    chunk_id=chunk_id,
                    document_id=metadata.get('document_id', 'unknown')
                )
                
                knowledge_chunks.append(knowledge_chunk)
            
            return knowledge_chunks
            
        except Exception as e:
            logger.error(f"Failed to retrieve knowledge for query '{query}': {e}")
            return []
    
    def rag_query(self, query: str, top_k: int = 3, 
                 use_llm: bool = True) -> Dict[str, Any]:
        """Perform a RAG query with optional LLM integration."""
        try:
            # Retrieve relevant knowledge
            knowledge_chunks = self.retrieve_relevant_knowledge(query, top_k=top_k)
            
            result = {
                "query": query,
                "retrieved_chunks": [],
                "context": "",
                "answer": None,
                "sources": []
            }
            
            # Build context from retrieved chunks
            context_parts = []
            sources = set()
            
            for chunk in knowledge_chunks:
                result["retrieved_chunks"].append({
                    "content": chunk.content,
                    "source": chunk.metadata.file_name,
                    "chunk_id": chunk.chunk_id
                })
                
                context_parts.append(chunk.content)
                sources.add(f"{chunk.metadata.file_name} (ID: {chunk.metadata.document_id})")
            
            result["context"] = "\n\n".join(context_parts)
            result["sources"] = list(sources)
            
            # If LLM integration is enabled, generate an answer
            if use_llm and knowledge_chunks:
                # In a real implementation, this would call the LLM
                # For now, we'll simulate it
                result["answer"] = self._simulate_llm_response(query, result["context"])
            
            return result
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {
                "query": query,
                "error": str(e),
                "retrieved_chunks": [],
                "context": "",
                "answer": None,
                "sources": []
            }
    
    def _simulate_llm_response(self, query: str, context: str) -> str:
        """Simulate LLM response for demonstration."""
        # In a real implementation, this would call the actual LLM
        # with a prompt that includes the context
        
        # Simple simulation: extract key information from context
        lines = context.split('\n')
        key_info = [line for line in lines if len(line) > 20]  # Simple heuristic
        
        return f"Based on the provided context, here's what I found about '{query}':\n\n" + 
               "\n".join(key_info[:3]) + 
               "\n\n[This is a simulated response - in production, an LLM would generate this]"
    
    def search_documents(self, query: str = None, 
                        filters: Optional[Dict] = None) -> List[Dict]:
        """Search for documents in the knowledge base."""
        try:
            if query:
                # Semantic search
                results = self.retrieve_relevant_knowledge(query, top_k=10, filters=filters)
                
                # Group by document
                documents = {}
                for chunk in results:
                    doc_id = chunk.metadata.document_id
                    if doc_id not in documents:
                        documents[doc_id] = {
                            "document_id": doc_id,
                            "file_name": chunk.metadata.file_name,
                            "source": chunk.metadata.source,
                            "language": chunk.metadata.language,
                            "chunks": []
                        }
                    documents[doc_id]["chunks"].append({
                        "chunk_id": chunk.chunk_id,
                        "content_preview": chunk.content[:100] + "..."
                    })
                
                return list(documents.values())
            else:
                # Simple metadata search
                all_items = self.collection.get()
                
                # Group by document
                documents = {}
                for i in range(len(all_items['ids'])):
                    doc_id = all_items['metadatas'][i].get('document_id')
                    if doc_id not in documents:
                        metadata = all_items['metadatas'][i]
                        documents[doc_id] = {
                            "document_id": doc_id,
                            "file_name": metadata.get('file_name', 'unknown'),
                            "source": metadata.get('source', 'unknown'),
                            "language": metadata.get('language', 'unknown'),
                            "chunks": []
                        }
                    
                    documents[doc_id]["chunks"].append({
                        "chunk_id": all_items['ids'][i],
                        "content_preview": all_items['documents'][i][:100] + "..."
                    })
                
                return list(documents.values())
                
        except Exception as e:
            logger.error(f"Document search failed: {e}")
            return []
    
    def get_document_info(self, document_id: str) -> Optional[Dict]:
        """Get information about a specific document."""
        try:
            # Query for chunks belonging to this document
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if not results['ids']:
                return None
            
            # Get metadata from first chunk
            metadata = results['metadatas'][0]
            
            return {
                "document_id": document_id,
                "file_name": metadata.get('file_name', 'unknown'),
                "source": metadata.get('source', 'unknown'),
                "language": metadata.get('language', 'unknown'),
                "total_chunks": len(results['ids']),
                "chunk_ids": results['ids'],
                "sample_content": results['documents'][0][:200] + "..." if results['documents'] else ""
            }
            
        except Exception as e:
            logger.error(f"Failed to get document info: {e}")
            return None
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the knowledge base."""
        try:
            # Find all chunks belonging to this document
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if results['ids']:
                # Delete the chunks
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted document {document_id} with {len(results['ids'])} chunks")
                return True
            else:
                logger.warning(f"Document {document_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        try:
            collection_info = self.collection.count()
            
            # Get unique documents
            all_items = self.collection.get()
            unique_documents = set()
            languages = set()
            sources = set()
            
            for metadata in all_items['metadatas']:
                unique_documents.add(metadata.get('document_id'))
                languages.add(metadata.get('language'))
                sources.add(metadata.get('source'))
            
            return {
                "total_chunks": collection_info,
                "unique_documents": len(unique_documents),
                "languages": list(languages),
                "sources": list(sources),
                "collection_name": self.collection_name
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}
    
    def shutdown(self):
        """Clean up resources."""
        try:
            if hasattr(self, 'chroma_client') and self.chroma_client:
                self.chroma_client.__exit__(None, None, None)
            logger.info("KnowledgeBaseRAG shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Example usage and testing
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Create knowledge base
    kb = KnowledgeBaseRAG()
    
    # Example: Ingest a text file (create a sample file first)
    sample_text = """
    ARCHER is an advanced AI assistant designed for Windows systems.
    It features voice interaction, computer vision, and multi-agent coordination.
    The system uses a 4-tier memory architecture for comprehensive knowledge management.
    """
    
    # Write sample text to file
    with open("sample_knowledge.txt", "w") as f:
        f.write(sample_text)
    
    # Ingest the file
    result = kb.ingest_document("sample_knowledge.txt")
    print("Ingestion result:", result)
    
    # Test RAG query
    query_result = kb.rag_query("What is ARCHER?")
    print("\nRAG Query Result:")
    print(f"Query: {query_result['query']}")
    print(f"Answer: {query_result['answer']}")
    print(f"Sources: {query_result['sources']}")
    
    # Get stats
    stats = kb.get_stats()
    print(f"\nKnowledge Base Stats: {stats}")
    
    # Clean up
    import os
    if os.path.exists("sample_knowledge.txt"):
        os.remove("sample_knowledge.txt")
    
    kb.shutdown()