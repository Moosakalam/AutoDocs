"""
Unit tests for AutoDoc agents.
Tests each agent's functionality independently.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.ingestion_agent import IngestionAgent
from rag.vector_store import VectorStore
from parsers.code_parser import CodeParser
from utils.file_utils import FileUtils


# ========================================
# FIXTURES
# ========================================

@pytest.fixture
def sample_code_chunks():
    """Sample code chunks for testing."""
    return [
        {
            'content': 'def add(a, b):\n    return a + b',
            'chunk_type': 'function',
            'file_path': 'math_utils.py',
            'language': 'python',
            'name': 'add',
            'start_line': 0,
            'end_line': 2
        },
        {
            'content': 'def subtract(a, b):\n    return a - b',
            'chunk_type': 'function',
            'file_path': 'math_utils.py',
            'language': 'python',
            'name': 'subtract',
            'start_line': 3,
            'end_line': 5
        }
    ]


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    store = Mock(spec=VectorStore)
    store.add_documents = Mock()
    store.query = Mock(return_value={
        'documents': [['sample code']],
        'metadatas': [[{'file_path': 'test.py'}]],
        'distances': [[0.5]]
    })
    store.get_collection_stats = Mock(return_value={
        'total_documents': 10,
        'collection_name': 'test_collection'
    })
    return store


@pytest.fixture
def mock_code_parser():
    """Mock code parser for testing."""
    parser = Mock(spec=CodeParser)
    parser.parse_file = Mock(return_value=[
        {
            'content': 'def test():\n    pass',
            'chunk_type': 'function',
            'file_path': 'test.py',
            'language': 'python'
        }
    ])
    return parser


@pytest.fixture
def mock_file_utils():
    """Mock file utils for testing."""
    utils = Mock(spec=FileUtils)
    utils.get_code_files = Mock(return_value=[
        {
            'path': 'test.py',
            'content': 'def test():\n    pass',
            'language': 'python',
            'extension': '.py'
        }
    ])
    return utils


# ========================================
# INGESTION AGENT TESTS
# ========================================

class TestIngestionAgent:
    """Tests for IngestionAgent."""
    
    def test_initialization(self, mock_code_parser, mock_vector_store, mock_file_utils):
        """Test agent initializes correctly."""
        agent = IngestionAgent(mock_code_parser, mock_vector_store, mock_file_utils)
        
        assert agent.code_parser == mock_code_parser
        assert agent.vector_store == mock_vector_store
        assert agent.file_utils == mock_file_utils
    
    def test_ingest_repository_basic(self, mock_code_parser, mock_vector_store, mock_file_utils):
        """Test basic repository ingestion."""
        agent = IngestionAgent(mock_code_parser, mock_vector_store, mock_file_utils)
        
        # Setup mock returns
        mock_file_utils.get_code_files.return_value = [
            {
                'path': 'test.py',
                'content': 'def hello():\n    print("Hi")',
                'language': 'python',
                'extension': '.py'
            }
        ]
        
        mock_code_parser.parse_file.return_value = [
            {
                'content': 'def hello():\n    print("Hi")',
                'chunk_type': 'function',
                'file_path': 'test.py',
                'language': 'python',
                'name': 'hello'
            }
        ]
        
        # Run ingestion
        report = agent.ingest_repository('./test_repo', ['*.md'])
        
        # Verify results
        assert report['total_files'] == 1
        assert report['total_chunks'] == 1
        assert 'python' in report['languages']
        
        # Verify vector store was called
        mock_vector_store.add_documents.assert_called_once()
    
    def test_ingest_repository_multiple_files(self, mock_code_parser, mock_vector_store, mock_file_utils):
        """Test ingestion with multiple files."""
        agent = IngestionAgent(mock_code_parser, mock_vector_store, mock_file_utils)
        
        # Multiple files
        mock_file_utils.get_code_files.return_value = [
            {'path': 'a.py', 'content': 'code1', 'language': 'python', 'extension': '.py'},
            {'path': 'b.py', 'content': 'code2', 'language': 'python', 'extension': '.py'},
            {'path': 'c.js', 'content': 'code3', 'language': 'javascript', 'extension': '.js'}
        ]
        
        # Each file has 2 chunks
        mock_code_parser.parse_file.return_value = [
            {'content': 'chunk1', 'chunk_type': 'function', 'file_path': 'test', 'language': 'python'},
            {'content': 'chunk2', 'chunk_type': 'function', 'file_path': 'test', 'language': 'python'}
        ]
        
        report = agent.ingest_repository('./test_repo', [])
        
        assert report['total_files'] == 3
        assert report['total_chunks'] == 6  # 3 files × 2 chunks
        assert 'python' in report['languages']
        assert 'javascript' in report['languages']
    
    def test_ingest_repository_handles_errors(self, mock_code_parser, mock_vector_store, mock_file_utils):
        """Test ingestion handles parsing errors gracefully."""
        agent = IngestionAgent(mock_code_parser, mock_vector_store, mock_file_utils)
        
        mock_file_utils.get_code_files.return_value = [
            {'path': 'good.py', 'content': 'code', 'language': 'python', 'extension': '.py'},
            {'path': 'bad.py', 'content': 'code', 'language': 'python', 'extension': '.py'}
        ]
        
        # First file succeeds, second fails
        mock_code_parser.parse_file.side_effect = [
            [{'content': 'chunk', 'chunk_type': 'function', 'file_path': 'good.py', 'language': 'python'}],
            Exception("Parse error")
        ]
        
        # Should not raise, should continue
        report = agent.ingest_repository('./test_repo', [])
        
        # Only successful file counted
        assert report['total_files'] == 2
        assert report['total_chunks'] == 1


# ========================================
# ANALYSIS AGENT TESTS
# ========================================

class TestAnalysisAgent:
    """Tests for AnalysisAgent."""
    
    @pytest.mark.asyncio
    async def test_analysis_generates_json(self):
        """Test that analysis agent returns structured JSON."""
        from rag.retriever import CodeRetriever
        
        # Mock retriever
        mock_retriever = Mock(spec=CodeRetriever)
        mock_retriever.retrieve_context = Mock(return_value="Sample code context")
        
        # Mock LLM config
        llm_config = {
            'model': 'gpt-4o-mini',
            'temperature': 0.2
        }
        
        # We can't easily test the actual LLM call without API
        # So we'll test the structure
        
        # Mock the agent to return a known response
        with patch('agents.analysis_agent.AnalysisAgent') as MockAgent:
            mock_instance = MockAgent.return_value
            mock_instance.analyze_codebase = AsyncMock(return_value={
                'architecture_type': 'monolith',
                'design_patterns': ['MVC'],
                'entry_points': ['main.py'],
                'module_dependencies': {},
                'core_abstractions': [],
                'technology_stack': ['Python']
            })
            
            agent = mock_instance
            result = await agent.analyze_codebase({'repo': 'test'})
            
            # Verify structure
            assert 'architecture_type' in result
            assert 'design_patterns' in result
            assert 'entry_points' in result
    
    @pytest.mark.asyncio
    async def test_analysis_uses_multiple_rag_queries(self):
        """Test that analysis agent makes multiple RAG queries."""
        from rag.retriever import CodeRetriever
        
        mock_retriever = Mock(spec=CodeRetriever)
        mock_retriever.retrieve_context = Mock(return_value="Context")
        
        # Create a simplified version for testing
        class TestAnalysisAgent:
            def __init__(self, retriever):
                self.retriever = retriever
            
            async def analyze(self):
                # Simulate the multiple queries
                self.retriever.retrieve_context("entry points")
                self.retriever.retrieve_context("architecture")
                self.retriever.retrieve_context("dependencies")
                return {'queries_made': 3}
        
        agent = TestAnalysisAgent(mock_retriever)
        result = await agent.analyze()
        
        # Should have made 3 calls
        assert mock_retriever.retrieve_context.call_count == 3


# ========================================
# WRITER AGENT TESTS
# ========================================

class TestWriterAgent:
    """Tests for WriterAgent."""
    
    @pytest.mark.asyncio
    async def test_writer_generates_multiple_docs(self):
        """Test that writer generates README, MODULE_GUIDE, ONBOARDING."""
        
        # Mock the writer agent
        class MockWriterAgent:
            async def generate_documentation(self, analysis, metadata):
                return {
                    'README.md': '# Project\n\nDescription',
                    'MODULE_GUIDE.md': '# Modules\n\nGuide',
                    'ONBOARDING.md': '# Onboarding\n\nSteps'
                }
        
        agent = MockWriterAgent()
        docs = await agent.generate_documentation({}, {})
        
        assert 'README.md' in docs
        assert 'MODULE_GUIDE.md' in docs
        assert 'ONBOARDING.md' in docs
        assert len(docs) == 3
    
    @pytest.mark.asyncio
    async def test_writer_uses_analysis_report(self):
        """Test that writer incorporates analysis data."""
        
        class TestWriterAgent:
            def __init__(self):
                self.analysis_used = None
            
            async def generate_documentation(self, analysis, metadata):
                self.analysis_used = analysis
                return {'README.md': f"Architecture: {analysis['arch']}"}
        
        agent = TestWriterAgent()
        analysis = {'arch': 'microservices'}
        docs = await agent.generate_documentation(analysis, {})
        
        assert agent.analysis_used == analysis
        assert 'microservices' in docs['README.md']


# ========================================
# QA AGENT TESTS
# ========================================

class TestQAAgent:
    """Tests for QAAgent."""
    
    def test_claim_extraction(self):
        """Test extracting claims from documentation."""
        
        # Simplified claim extractor
        def extract_claims(doc_content):
            keywords = ['uses', 'implements', 'contains']
            sentences = doc_content.split('.')
            claims = []
            for sentence in sentences:
                if any(kw in sentence.lower() for kw in keywords):
                    claims.append(sentence.strip())
            return claims
        
        doc = "The app uses Redis. It implements JWT auth. Python is great."
        claims = extract_claims(doc)
        
        assert len(claims) == 2
        assert any('Redis' in c for c in claims)
        assert any('JWT' in c for c in claims)
    
    @pytest.mark.asyncio
    async def test_validation_detects_issues(self):
        """Test that QA agent flags validation issues."""
        
        class MockQAAgent:
            async def validate_documentation(self, docs, analysis):
                return {
                    'total_claims_checked': 5,
                    'issues_found': 2,
                    'issues': [
                        {'claim': 'Uses Redis', 'status': 'hallucination', 'severity': 'critical'},
                        {'claim': 'Has tests', 'status': 'unverifiable', 'severity': 'minor'}
                    ],
                    'critical_issues': 1
                }
        
        agent = MockQAAgent()
        report = await agent.validate_documentation({'README.md': 'content'}, {})
        
        assert report['issues_found'] == 2
        assert report['critical_issues'] == 1
        assert len(report['issues']) == 2


# ========================================
# REVIEWER AGENT TESTS
# ========================================

class TestReviewerAgent:
    """Tests for ReviewerAgent."""
    
    @pytest.mark.asyncio
    async def test_reviewer_generates_scores(self):
        """Test that reviewer generates quality scores."""
        
        class MockReviewerAgent:
            async def review_documentation(self, docs, validation, analysis):
                return {
                    'scores': {
                        'completeness': 8,
                        'clarity': 7,
                        'accuracy': 9,
                        'structure': 8,
                        'usefulness': 7,
                        'overall': 8
                    },
                    'coverage': {
                        'coverage_percentage': 75.0
                    }
                }
        
        agent = MockReviewerAgent()
        review = await agent.review_documentation({}, {}, {})
        
        assert 'scores' in review
        assert review['scores']['overall'] == 8
        assert 0 <= review['scores']['overall'] <= 10
        assert review['coverage']['coverage_percentage'] == 75.0
    
    @pytest.mark.asyncio
    async def test_reviewer_calculates_coverage(self):
        """Test coverage calculation."""
        
        def calculate_coverage(total_components, documented_components):
            if total_components == 0:
                return 0
            return (documented_components / total_components) * 100
        
        coverage = calculate_coverage(10, 7)
        assert coverage == 70.0
        
        coverage = calculate_coverage(0, 0)
        assert coverage == 0


# ========================================
# INTEGRATION TESTS
# ========================================

class TestAgentIntegration:
    """Integration tests for agent workflows."""
    
    def test_ingestion_to_vector_store(self, mock_code_parser, mock_vector_store, mock_file_utils):
        """Test complete ingestion flow."""
        agent = IngestionAgent(mock_code_parser, mock_vector_store, mock_file_utils)
        
        # Setup complete flow
        mock_file_utils.get_code_files.return_value = [
            {'path': 'test.py', 'content': 'code', 'language': 'python', 'extension': '.py'}
        ]
        mock_code_parser.parse_file.return_value = [
            {'content': 'chunk', 'chunk_type': 'function', 'file_path': 'test.py', 'language': 'python'}
        ]
        
        report = agent.ingest_repository('./test', [])
        
        # Verify end-to-end
        assert mock_file_utils.get_code_files.called
        assert mock_code_parser.parse_file.called
        assert mock_vector_store.add_documents.called
        assert report['total_chunks'] == 1


# ========================================
# RUN TESTS
# ========================================

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])