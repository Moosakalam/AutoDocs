"""
File utilities for reading and processing repository files.
Handles file filtering, extension checking, and content reading.
"""
import os
from pathlib import Path
from typing import List, Dict
import fnmatch

class FileUtils:
    """Utility class for file operations in repository processing."""
    
    @staticmethod
    def get_code_files(repo_path: str, exclude_patterns: List[str]) -> List[Dict[str, str]]:
        """
        Recursively get all code files from repository.
        
        Args:
            repo_path: Path to repository root
            exclude_patterns: Glob patterns to exclude (e.g., ['*.md', 'node_modules/**'])
        
        Returns:
            List of dicts with 'path', 'extension', 'content'
        """
        code_files = []
        supported_extensions = {'.py', '.js', '.java', '.ts', '.jsx', '.tsx', '.cpp', '.c', '.go'}
        
        for root, dirs, files in os.walk(repo_path):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not any(
                fnmatch.fnmatch(d, pattern) for pattern in exclude_patterns
            )]
            
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(repo_path)
                
                # Check if file should be excluded
                if any(fnmatch.fnmatch(str(relative_path), pattern) 
                       for pattern in exclude_patterns):
                    continue
                
                # Check if file is a supported code file
                if file_path.suffix in supported_extensions:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        code_files.append({
                            'path': str(relative_path),
                            'absolute_path': str(file_path),
                            'extension': file_path.suffix,
                            'content': content,
                            'language': FileUtils._get_language(file_path.suffix)
                        })
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
        
        return code_files
    
    @staticmethod
    def _get_language(extension: str) -> str:
        """Map file extension to language name."""
        mapping = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go'
        }
        return mapping.get(extension, 'unknown')