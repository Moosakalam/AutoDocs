"""
Retriever class that wraps vector store queries with formatting.
"""
from typing import List, Dict
from .vector_store import VectorStore

class CodeRetriever:
    """Retrieves relevant code chunks for RAG queries."""
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
    
    def retrieve_context(self, query: str, n_results: int = 5, 
                        language_filter: str = None) -> str:
        """
        Retrieve relevant code chunks and format as context.
        
        Args:
            query: Query string
            n_results: Number of chunks to retrieve
            language_filter: Filter by programming language
        
        Returns:
            Formatted context string for LLM
        """
        # Build metadata filter
        where_filter = {'language': language_filter} if language_filter else None
        
        # Query vector store
        results = self.vector_store.query(
            query_text=query,
            n_results=n_results,
            filter_metadata=where_filter
        )
        
        # Format results as context
        context_parts = []
        for idx, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            context_parts.append(
                f"--- Chunk {idx + 1} (from {metadata['file_path']}) ---\n"
                f"Type: {metadata.get('chunk_type', 'unknown')}\n"
                f"Language: {metadata.get('language', 'unknown')}\n"
                f"Relevance: {1 - distance:.3f}\n\n"
                f"{doc}\n"
            )
        
        return "\n".join(context_parts)
    
    def retrieve_by_file(self, file_path: str) -> List[Dict]:
        """Retrieve all chunks from a specific file."""
        results = self.vector_store.query(
            query_text="",  # Empty query
            n_results=1000,  # Get many results
            filter_metadata={'file_path': file_path}
        )
        
        return [
            {'content': doc, 'metadata': meta}
            for doc, meta in zip(results['documents'][0], results['metadatas'][0])
        ]