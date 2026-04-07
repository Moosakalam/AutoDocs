"""
Chunking strategies for different code scenarios.
Provides multiple approaches to splitting code into meaningful chunks.
"""

from typing import List, Dict
from enum import Enum


class ChunkStrategy(Enum):
    """Available chunking strategies."""
    SEMANTIC = "semantic"  # AST-based (functions, classes)
    LINE_BASED = "line_based"  # Fixed number of lines
    TOKEN_BASED = "token_based"  # Fixed number of tokens
    HYBRID = "hybrid"  # Combination of semantic + size limits


class CodeChunker:
    """
    Manages different chunking strategies for code.
    Decides which strategy to use based on file characteristics.
    """
    
    def __init__(self, max_chunk_size: int = 1000, overlap: int = 100):
        """
        Initialize chunker with size constraints.
        
        Args:
            max_chunk_size: Maximum characters per chunk
            overlap: Number of overlapping characters between chunks
        """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
    
    def chunk_by_lines(self, content: str, file_path: str, 
                      lines_per_chunk: int = 50) -> List[Dict]:
        """
        Line-based chunking strategy.
        Use when: File has no clear structure, or AST parsing fails.
        
        Args:
            content: Source code content
            file_path: File path for metadata
            lines_per_chunk: Number of lines per chunk
        
        Returns:
            List of chunks with metadata
        """
        lines = content.split('\n')
        chunks = []
        
        for i in range(0, len(lines), lines_per_chunk - self.overlap // 10):
            # Calculate overlap in lines (rough approximation)
            overlap_lines = self.overlap // 10  # Assume ~10 chars per line
            
            start_idx = max(0, i - overlap_lines) if i > 0 else 0
            end_idx = min(i + lines_per_chunk, len(lines))
            
            chunk_lines = lines[start_idx:end_idx]
            chunk_content = '\n'.join(chunk_lines)
            
            chunks.append({
                'content': chunk_content,
                'chunk_type': 'line_chunk',
                'file_path': file_path,
                'start_line': start_idx,
                'end_line': end_idx,
                'chunk_index': i // lines_per_chunk,
                'strategy': ChunkStrategy.LINE_BASED.value
            })
        
        return chunks
    
    def chunk_by_tokens(self, content: str, file_path: str, 
                       tokens_per_chunk: int = 500) -> List[Dict]:
        """
        Token-based chunking strategy.
        Use when: Need precise control over LLM context usage.
        
        Args:
            content: Source code content
            file_path: File path for metadata
            tokens_per_chunk: Target tokens per chunk
        
        Returns:
            List of chunks with metadata
        """
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            # Fallback to character-based approximation
            # Rough estimate: 1 token ≈ 4 characters
            return self._chunk_by_characters(
                content, file_path, 
                chars_per_chunk=tokens_per_chunk * 4
            )
        
        # Encode entire content
        tokens = encoding.encode(content)
        chunks = []
        
        overlap_tokens = self.overlap // 4  # Rough token estimate
        
        for i in range(0, len(tokens), tokens_per_chunk - overlap_tokens):
            start_idx = max(0, i - overlap_tokens) if i > 0 else 0
            end_idx = min(i + tokens_per_chunk, len(tokens))
            
            chunk_tokens = tokens[start_idx:end_idx]
            chunk_content = encoding.decode(chunk_tokens)
            
            chunks.append({
                'content': chunk_content,
                'chunk_type': 'token_chunk',
                'file_path': file_path,
                'token_count': len(chunk_tokens),
                'chunk_index': i // tokens_per_chunk,
                'strategy': ChunkStrategy.TOKEN_BASED.value
            })
        
        return chunks
    
    def _chunk_by_characters(self, content: str, file_path: str,
                            chars_per_chunk: int = 2000) -> List[Dict]:
        """
        Character-based chunking (internal fallback).
        
        Args:
            content: Source code content
            file_path: File path for metadata
            chars_per_chunk: Characters per chunk
        
        Returns:
            List of chunks with metadata
        """
        chunks = []
        
        for i in range(0, len(content), chars_per_chunk - self.overlap):
            start_idx = max(0, i - self.overlap) if i > 0 else 0
            end_idx = min(i + chars_per_chunk, len(content))
            
            chunk_content = content[start_idx:end_idx]
            
            chunks.append({
                'content': chunk_content,
                'chunk_type': 'char_chunk',
                'file_path': file_path,
                'char_start': start_idx,
                'char_end': end_idx,
                'chunk_index': i // chars_per_chunk,
                'strategy': ChunkStrategy.TOKEN_BASED.value  # Fallback for token-based
            })
        
        return chunks
    
    def chunk_hybrid(self, semantic_chunks: List[Dict], 
                    file_path: str) -> List[Dict]:
        """
        Hybrid chunking strategy.
        Combines semantic chunks but splits large ones.
        
        Use when: AST parsing works but some functions/classes are huge.
        
        Args:
            semantic_chunks: Chunks from AST parsing
            file_path: File path for metadata
        
        Returns:
            List of refined chunks
        """
        refined_chunks = []
        
        for chunk in semantic_chunks:
            content = chunk['content']
            
            # If chunk is within size limit, keep as-is
            if len(content) <= self.max_chunk_size:
                chunk['strategy'] = ChunkStrategy.HYBRID.value
                refined_chunks.append(chunk)
            else:
                # Split large semantic chunk using line-based strategy
                print(f"  ⚠ Large {chunk['chunk_type']} detected ({len(content)} chars), splitting...")
                
                sub_chunks = self.chunk_by_lines(
                    content, 
                    file_path,
                    lines_per_chunk=self.max_chunk_size // 50  # Rough estimate
                )
                
                # Add metadata indicating this came from a semantic chunk
                for sub_chunk in sub_chunks:
                    sub_chunk['parent_type'] = chunk['chunk_type']
                    sub_chunk['parent_name'] = chunk.get('name', 'unknown')
                    sub_chunk['strategy'] = ChunkStrategy.HYBRID.value
                
                refined_chunks.extend(sub_chunks)
        
        return refined_chunks
    
    def decide_strategy(self, content: str, language: str, 
                       has_ast: bool) -> ChunkStrategy:
        """
        Automatically decide which chunking strategy to use.
        
        Args:
            content: Source code content
            language: Programming language
            has_ast: Whether AST parsing is available
        
        Returns:
            Recommended chunking strategy
        """
        # If AST parsing available, prefer semantic
        if has_ast:
            # Check if file is reasonably sized
            if len(content) < 50000:  # ~50KB
                return ChunkStrategy.SEMANTIC
            else:
                # Large file - use hybrid
                return ChunkStrategy.HYBRID
        
        # No AST - decide between line and token based
        if len(content) < 10000:
            return ChunkStrategy.LINE_BASED
        else:
            return ChunkStrategy.TOKEN_BASED


class ContextWindowManager:
    """
    Manages chunks to fit within LLM context windows.
    Useful for retrieval result optimization.
    """
    
    def __init__(self, max_context_tokens: int = 8000):
        """
        Initialize context window manager.
        
        Args:
            max_context_tokens: Maximum tokens for context
        """
        self.max_context_tokens = max_context_tokens
    
    def fit_chunks_to_context(self, chunks: List[Dict], 
                             query: str = "") -> List[Dict]:
        """
        Select chunks that fit within context window.
        
        Args:
            chunks: Retrieved chunks (sorted by relevance)
            query: Original query (to budget for it)
        
        Returns:
            Subset of chunks that fit in context
        """
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            
            # Budget tokens for query
            query_tokens = len(encoding.encode(query))
            available_tokens = self.max_context_tokens - query_tokens - 500  # Buffer
            
            selected_chunks = []
            current_tokens = 0
            
            for chunk in chunks:
                chunk_tokens = len(encoding.encode(chunk['content']))
                
                if current_tokens + chunk_tokens <= available_tokens:
                    selected_chunks.append(chunk)
                    current_tokens += chunk_tokens
                else:
                    # Context full
                    break
            
            print(f"  Context usage: {current_tokens}/{available_tokens} tokens ({len(selected_chunks)} chunks)")
            return selected_chunks
            
        except ImportError:
            # Fallback: character-based approximation
            char_limit = self.max_context_tokens * 4
            selected_chunks = []
            current_chars = len(query)
            
            for chunk in chunks:
                chunk_chars = len(chunk['content'])
                
                if current_chars + chunk_chars <= char_limit:
                    selected_chunks.append(chunk)
                    current_chars += chunk_chars
                else:
                    break
            
            return selected_chunks
    
    def prioritize_chunks(self, chunks: List[Dict], 
                         priority_types: List[str] = None) -> List[Dict]:
        """
        Reorder chunks based on priority.
        
        Args:
            chunks: List of chunks
            priority_types: Chunk types to prioritize (e.g., ['function', 'class'])
        
        Returns:
            Reordered chunks
        """
        if not priority_types:
            priority_types = ['function', 'class', 'method']
        
        # Separate into priority and non-priority
        priority_chunks = [c for c in chunks if c.get('chunk_type') in priority_types]
        other_chunks = [c for c in chunks if c.get('chunk_type') not in priority_types]
        
        # Priority chunks first, then others
        return priority_chunks + other_chunks


# Example usage patterns:
"""
# Basic line-based chunking:
chunker = CodeChunker(max_chunk_size=1000, overlap=100)
chunks = chunker.chunk_by_lines(code_content, "main.py")

# Token-based for precise control:
chunks = chunker.chunk_by_tokens(code_content, "main.py", tokens_per_chunk=500)

# Hybrid for large semantic chunks:
semantic_chunks = ast_parser.extract_chunks(code)
refined_chunks = chunker.chunk_hybrid(semantic_chunks, "main.py")

# Automatic strategy selection:
strategy = chunker.decide_strategy(code_content, "python", has_ast=True)

# Context window management:
context_manager = ContextWindowManager(max_context_tokens=8000)
fitted_chunks = context_manager.fit_chunks_to_context(retrieved_chunks, query)
"""