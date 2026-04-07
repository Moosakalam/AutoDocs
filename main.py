"""
AutoDoc - Multi-Agent Codebase Documentation System
Main entry point

Usage:
    python main.py --repo-url https://github.com/user/repo
    python main.py --repo-path ./local/repo
"""
from typing import Dict
import asyncio
import argparse
import yaml
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_core.models import ModelInfo
from utils.file_utils import FileUtils
from utils.git_utils import GitUtils
from rag.vector_store import VectorStore
from rag.retriever import CodeRetriever
from parsers.code_parser import CodeParser
from agents.ingestion_agent import IngestionAgent
from agents.analysis_agent import AnalysisAgent
from agents.writer_agent import WriterAgent
from agents.qa_agent import QAAgent
from agents.reviewer_agent import ReviewerAgent
from orchestration.workflow import AutoDocOrchestrator


def load_config():
    """Load configuration from YAML file."""
    config_path = Path(__file__).parent / "config" / "config.yaml"
    
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("Creating default configuration...")
        create_default_config()
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def create_default_config():
    """Create default configuration file."""
    config_dir = Path(__file__).parent / "config"
    config_dir.mkdir(exist_ok=True)
    
    default_config = {
        'llm': {
            'model': 'gpt-4o-mini',
            'temperature': 0.2,
            'max_tokens': 4000
        },
        'embeddings': {
            'model': 'text-embedding-3-small',
            'dimension': 1536
        },
        'chromadb': {
            'persist_directory': './chroma_db',
            'collection_name': 'codebase_embeddings'
        },
        'parsing': {
            'max_chunk_size': 1000,
            'overlap': 100,
            'supported_languages': ['python', 'javascript', 'java']
        },
        'repository': {
            'clone_depth': 1,
            'exclude_patterns': [
                '*.md',
                '*.txt',
                'node_modules/**',
                '__pycache__/**',
                '*.pyc',
                '.git/**',
                'venv/**',
                'env/**'
            ]
        }
    }
    
    config_path = config_dir / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False)
    
    print(f"✅ Default configuration created at {config_path}")


async def main():
    """Main entry point for AutoDoc."""
    
    parser = argparse.ArgumentParser(
        description="AutoDoc - Multi-Agent Codebase Documentation System"
    )
    parser.add_argument(
        '--repo-url',
        type=str,
        help='GitHub repository URL to document'
    )
    parser.add_argument(
        '--repo-path',
        type=str,
        help='Local repository path to document'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./output',
        help='Output directory for generated documentation (default: ./output)'
    )
    parser.add_argument(
        '--reset-db',
        action='store_true',
        help='Reset ChromaDB before ingestion'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.repo_url and not args.repo_path:
        print("❌ Error: Must provide either --repo-url or --repo-path")
        parser.print_help()
        return
    
    # Load environment variables
    load_dotenv()
    
    # Verify API key
    if not os.getenv('OPENAI_API_KEY') and not os.getenv('GOOGLE_API_KEY'):
        print("❌ Error: No API key found!")
        print("\nPlease create a .env file with one of:")
        print("  OPENAI_API_KEY=your_openai_key")
        print("  GOOGLE_API_KEY=your_gemini_key")
        return
    
    # Load configuration
    config = load_config()
    
    # Initialize orchestrator
    print("\n" + "="*80)
    print("🚀 AutoDoc - Multi-Agent Documentation System")
    print("="*80)
    
    orchestrator = AutoDocOrchestrator(config)
    
    # Reset database if requested
    if args.reset_db:
        print("\n🔄 Resetting ChromaDB...")
        orchestrator.vector_store.reset_collection()
    
    # Run pipeline
    try:
        results = await orchestrator.run_full_pipeline(
            repo_url=args.repo_url,
            repo_path=args.repo_path,
            output_dir=args.output_dir
        )
        
        print("\n✨ Success! Documentation generated.")
        print(f"\n📁 Output location: {args.output_dir}")
        print("\nGenerated files:")
        print("  - README.md (comprehensive project overview)")
        print("  - MODULE_GUIDE.md (module-level documentation)")
        print("  - ONBOARDING.md (developer onboarding guide)")
        print("  - AUTODOC_REPORT.md (quality report)")
        print("  - analysis_report.json (codebase analysis)")
        print("  - validation_report.json (QA validation)")
        print("  - quality_review.json (quality metrics)")
        
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())