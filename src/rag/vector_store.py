"""
Vector store implementation using ChromaDB.
Handles embedding storage, retrieval, and metadata management.
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import hashlib

class VectorStore:
    """ChromaDB vector store for code embeddings."""
    
    def __init__(self, persist_directory: str, collection_name: str):
        """
        Initialize ChromaDB client and collection.
        
        Args:
            persist_directory: Path to persist ChromaDB data
            collection_name: Name of the collection
        """
        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Code embeddings for documentation generation"}
        )
        
        print(f"ChromaDB collection '{collection_name}' initialized")
    
    def add_documents(self, documents: List[str], metadatas: List[Dict], 
                     embeddings: Optional[List[List[float]]] = None):
        """
        Add documents to vector store.
        
        Args:
            documents: List of text chunks
            metadatas: List of metadata dicts for each chunk
            embeddings: Pre-computed embeddings (optional, ChromaDB can compute)
        """
        # Generate unique IDs based on content hash
        ids = [self._generate_id(doc, meta) for doc, meta in zip(documents, metadatas)]
        
        if embeddings:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
                ids=ids
            )
        else:
            # Let ChromaDB compute embeddings
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        
        print(f"Added {len(documents)} documents to vector store")
    
    def query(self, query_text: str, n_results: int = 5, 
             filter_metadata: Optional[Dict] = None) -> Dict:
        """
        Query vector store for similar documents.
        
        Args:
            query_text: Query string
            n_results: Number of results to return
            filter_metadata: Metadata filters (e.g., {'language': 'python'})
        
        Returns:
            Query results with documents, distances, metadatas
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=filter_metadata
        )
        
        return results
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection."""
        count = self.collection.count()
        return {
            'total_documents': count,
            'collection_name': self.collection.name
        }
    
    def reset_collection(self):
        """Delete and recreate collection (for testing)."""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.create_collection(
            name=self.collection.name,
            metadata={"description": "Code embeddings for documentation generation"}
        )
        print("Collection reset")
    
    @staticmethod
    def _generate_id(document: str, metadata: Dict) -> str:
        """Generate deterministic ID from content and metadata."""
        content = f"{document}{metadata.get('file_path', '')}{metadata.get('chunk_index', '')}"
        return hashlib.md5(content.encode()).hexdigest()