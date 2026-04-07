"""
Ingestion Agent: Reads repository, parses code, stores in vector database.
"""
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from typing import List, Dict
import sys
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo
import json
import os 
from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient
sys.path.append('..')

class IngestionAgent:
    """Agent responsible for ingesting codebase into vector store."""
    
    def __init__(self, code_parser, vector_store, file_utils):
        """
        Initialize ingestion agent.
        
        Args:
            code_parser: CodeParser instance
            vector_store: VectorStore instance
            file_utils: FileUtils instance
        """
        self.code_parser = code_parser
        self.vector_store = vector_store
        self.file_utils = file_utils
        
    def ingest_repository(self, repo_path: str, exclude_patterns: List[str]) -> Dict:
        """
        Main ingestion workflow.
        
        Args:
            repo_path: Path to repository
            exclude_patterns: Files/folders to exclude
        
        Returns:
            Ingestion report
        """
        print(f"\n=== INGESTION AGENT STARTED ===")
        print(f"Repository: {repo_path}")
        
        # Step 1: Get all code files
        print("\n[1/3] Discovering code files...")
        code_files = self.file_utils.get_code_files(repo_path, exclude_patterns)
        print(f"Found {len(code_files)} code files")
        
        # Step 2: Parse files into chunks
        print("\n[2/3] Parsing files with tree-sitter...")
        all_chunks = []
        for file_info in code_files:
            try:
                chunks = self.code_parser.parse_file(
                    file_content=file_info['content'],
                    language=file_info['language'],
                    file_path=file_info['path']
                )
                all_chunks.extend(chunks)
                print(f"  ✓ {file_info['path']}: {len(chunks)} chunks")
            except Exception as e:
                print(f"  ✗ {file_info['path']}: {e}")
        
        print(f"Total chunks created: {len(all_chunks)}")
        
        # Step 3: Store in vector database
        print("\n[3/3] Storing chunks in ChromaDB...")
        documents = [chunk['content'] for chunk in all_chunks]
        metadatas = [
            {
                'file_path': chunk['file_path'],
                'chunk_type': chunk['chunk_type'],
                'language': chunk['language'],
                'start_line': chunk.get('start_line', 0),
                'end_line': chunk.get('end_line', 0),
                'name': chunk.get('name', '')
            }
            for chunk in all_chunks
        ]
        
        self.vector_store.add_documents(documents, metadatas)
        
        # Generate report
        report = {
            'total_files': len(code_files),
            'total_chunks': len(all_chunks),
            'languages': list(set(chunk['language'] for chunk in all_chunks)),
            'chunk_types': {
                'functions': sum(1 for c in all_chunks if c['chunk_type'] == 'function'),
                'classes': sum(1 for c in all_chunks if c['chunk_type'] == 'class'),
                'line_chunks': sum(1 for c in all_chunks if c['chunk_type'] == 'line_chunk')
            }
        }
        
        print(f"\n=== INGESTION COMPLETE ===")
        print(f"Report: {report}")
        
        return report