"""
AST-based code parsing using tree-sitter.
Intelligently chunks code by semantic units (functions, classes, methods).
"""
from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_javascript
from typing import List, Dict
from pathlib import Path

class CodeParser:
    """Parses code files using tree-sitter AST."""
    
    def __init__(self):
        """Initialize tree-sitter parsers for supported languages."""
        # Build language parsers
        self.parsers = {
            'python': self._build_python_parser(),
            'javascript': self._build_javascript_parser()
        }
    
    def _build_python_parser(self) -> Parser:
        """Build Python parser."""
        PY_LANGUAGE = Language(tree_sitter_python.language())
        parser = Parser(PY_LANGUAGE)
        return parser
    
    def _build_javascript_parser(self) -> Parser:
        """Build JavaScript parser."""
        JS_LANGUAGE = Language(tree_sitter_javascript.language())
        parser = Parser(JS_LANGUAGE)
        return parser
    
    def parse_file(self, file_content: str, language: str, file_path: str) -> List[Dict]:
        """
        Parse a code file into semantic chunks.
        
        Args:
            file_content: Source code content
            language: Programming language
            file_path: File path (for metadata)
        
        Returns:
            List of chunks with metadata
        """
        if language not in self.parsers:
            # Fallback: simple line-based chunking
            return self._fallback_chunking(file_content, file_path, language)
        
        parser = self.parsers[language]
        tree = parser.parse(bytes(file_content, 'utf8'))
        
        chunks = []
        
        # Extract semantic units based on language
        if language == 'python':
            chunks = self._extract_python_chunks(tree.root_node, file_content, file_path)
        elif language == 'javascript':
            chunks = self._extract_javascript_chunks(tree.root_node, file_content, file_path)
        
        return chunks
    
    def _extract_python_chunks(self, root_node, source_code: str, file_path: str) -> List[Dict]:
        """Extract Python functions and classes as chunks."""
        chunks = []
        
        def visit_node(node, depth=0):
            # Extract function definitions
            if node.type == 'function_definition':
                chunks.append({
                    'content': self._get_node_text(node, source_code),
                    'chunk_type': 'function',
                    'file_path': file_path,
                    'language': 'python',
                    'start_line': node.start_point[0],
                    'end_line': node.end_point[0],
                    'name': self._get_function_name(node, source_code)
                })
            
            # Extract class definitions
            elif node.type == 'class_definition':
                chunks.append({
                    'content': self._get_node_text(node, source_code),
                    'chunk_type': 'class',
                    'file_path': file_path,
                    'language': 'python',
                    'start_line': node.start_point[0],
                    'end_line': node.end_point[0],
                    'name': self._get_class_name(node, source_code)
                })
            
            # Recursively visit child nodes
            for child in node.children:
                visit_node(child, depth + 1)
        
        visit_node(root_node)
        
        # If no chunks found, do line-based fallback
        if not chunks:
            chunks = self._fallback_chunking(source_code, file_path, 'python')
        
        return chunks
    
    def _extract_javascript_chunks(self, root_node, source_code: str, file_path: str) -> List[Dict]:
        """Extract JavaScript functions and classes as chunks."""
        chunks = []
        
        def visit_node(node):
            # Extract function declarations
            if node.type in ['function_declaration', 'arrow_function', 'function']:
                chunks.append({
                    'content': self._get_node_text(node, source_code),
                    'chunk_type': 'function',
                    'file_path': file_path,
                    'language': 'javascript',
                    'start_line': node.start_point[0],
                    'end_line': node.end_point[0]
                })
            
            # Extract class declarations
            elif node.type == 'class_declaration':
                chunks.append({
                    'content': self._get_node_text(node, source_code),
                    'chunk_type': 'class',
                    'file_path': file_path,
                    'language': 'javascript',
                    'start_line': node.start_point[0],
                    'end_line': node.end_point[0]
                })
            
            for child in node.children:
                visit_node(child)
        
        visit_node(root_node)
        
        if not chunks:
            chunks = self._fallback_chunking(source_code, file_path, 'javascript')
        
        return chunks
    
    def _get_node_text(self, node, source_code: str) -> str:
        """Extract text from AST node."""
        return source_code[node.start_byte:node.end_byte]
    
    def _get_function_name(self, node, source_code: str) -> str:
        """Extract function name from function node."""
        for child in node.children:
            if child.type == 'identifier':
                return self._get_node_text(child, source_code)
        return 'anonymous'
    
    def _get_class_name(self, node, source_code: str) -> str:
        """Extract class name from class node."""
        for child in node.children:
            if child.type == 'identifier':
                return self._get_node_text(child, source_code)
        return 'AnonymousClass'
    
    def _fallback_chunking(self, content: str, file_path: str, language: str) -> List[Dict]:
        """Fallback to simple line-based chunking if AST parsing fails."""
        lines = content.split('\n')
        chunk_size = 50  # Lines per chunk
        
        chunks = []
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i + chunk_size]
            chunks.append({
                'content': '\n'.join(chunk_lines),
                'chunk_type': 'line_chunk',
                'file_path': file_path,
                'language': language,
                'start_line': i,
                'end_line': min(i + chunk_size, len(lines)),
                'chunk_index': i // chunk_size
            })
        
        return chunks