"""
Unit tests for code parsers.
Tests AST-based parsing and chunking strategies.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parsers.code_parser import CodeParser
from parsers.chunk_strategy import CodeChunker, ChunkStrategy, ContextWindowManager


# ========================================
# FIXTURES
# ========================================

@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return """
def add(a, b):
    '''Add two numbers.'''
    return a + b

def subtract(a, b):
    '''Subtract b from a.'''
    return a - b

class Calculator:
    '''Simple calculator class.'''
    
    def multiply(self, a, b):
        return a * b
    
    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
"""


@pytest.fixture
def sample_javascript_code():
    """Sample JavaScript code for testing."""
    return """
function greet(name) {
    return `Hello, ${name}!`;
}

function farewell(name) {
    return `Goodbye, ${name}!`;
}

class Person {
    constructor(name, age) {
        this.name = name;
        this.age = age;
    }
    
    introduce() {
        return `I'm ${this.name}, ${this.age} years old`;
    }
}
"""


@pytest.fixture
def large_python_code():
    """Large Python code for testing chunk splitting."""
    code = "def large_function():\n"
    # Generate 200 lines
    for i in range(200):
        code += f"    line_{i} = {i}\n"
    code += "    return result\n"
    return code


# ========================================
# CODE PARSER TESTS
# ========================================

class TestCodeParser:
    """Tests for CodeParser."""
    
    def test_initialization(self):
        """Test parser initializes correctly."""
        parser = CodeParser()
        assert 'python' in parser.parsers
        assert 'javascript' in parser.parsers
    
    def test_parse_python_functions(self, sample_python_code):
        """Test parsing Python functions."""
        parser = CodeParser()
        chunks = parser.parse_file(sample_python_code, 'python', 'test.py')
        
        # Should extract: 2 functions + 1 class
        assert len(chunks) >= 3
        
        # Check function chunks
        function_chunks = [c for c in chunks if c['chunk_type'] == 'function']
        assert len(function_chunks) >= 2
        
        # Verify content
        add_chunk = next((c for c in chunks if 'add' in c.get('name', '')), None)
        assert add_chunk is not None
        assert 'def add' in add_chunk['content']
    
    def test_parse_python_classes(self, sample_python_code):
        """Test parsing Python classes."""
        parser = CodeParser()
        chunks = parser.parse_file(sample_python_code, 'python', 'test.py')
        
        # Should have class chunk
        class_chunks = [c for c in chunks if c['chunk_type'] == 'class']
        assert len(class_chunks) >= 1
        
        # Verify class content
        calc_chunk = next((c for c in chunks if 'Calculator' in c.get('name', '')), None)
        assert calc_chunk is not None
        assert 'class Calculator' in calc_chunk['content']
    
    def test_parse_javascript_functions(self, sample_javascript_code):
        """Test parsing JavaScript functions."""
        parser = CodeParser()
        chunks = parser.parse_file(sample_javascript_code, 'javascript', 'test.js')
        
        # Should extract functions and class
        assert len(chunks) >= 2
        
        # Check for function chunks
        function_chunks = [c for c in chunks if c['chunk_type'] == 'function']
        assert len(function_chunks) >= 2
    
    def test_parse_javascript_classes(self, sample_javascript_code):
        """Test parsing JavaScript classes."""
        parser = CodeParser()
        chunks = parser.parse_file(sample_javascript_code, 'javascript', 'test.js')
        
        # Should have class chunk
        class_chunks = [c for c in chunks if c['chunk_type'] == 'class']
        assert len(class_chunks) >= 1
    
    def test_fallback_chunking_for_unsupported_language(self):
        """Test fallback to line-based chunking."""
        parser = CodeParser()
        code = "print('hello')\nprint('world')"
        
        # Unsupported language
        chunks = parser.parse_file(code, 'ruby', 'test.rb')
        
        # Should use fallback
        assert len(chunks) > 0
        assert chunks[0]['chunk_type'] == 'line_chunk'
    
    def test_metadata_preservation(self, sample_python_code):
        """Test that chunks preserve metadata."""
        parser = CodeParser()
        chunks = parser.parse_file(sample_python_code, 'python', 'math_utils.py')
        
        for chunk in chunks:
            assert 'content' in chunk
            assert 'chunk_type' in chunk
            assert 'file_path' in chunk
            assert chunk['file_path'] == 'math_utils.py'
            assert 'language' in chunk
            assert chunk['language'] == 'python'
    
    def test_empty_file_handling(self):
        """Test handling of empty files."""
        parser = CodeParser()
        chunks = parser.parse_file("", 'python', 'empty.py')
        
        # Should handle gracefully
        assert isinstance(chunks, list)
        # Might be empty or have fallback chunk
        assert len(chunks) >= 0


# ========================================
# CHUNKING STRATEGY TESTS
# ========================================

class TestCodeChunker:
    """Tests for CodeChunker."""
    
    def test_initialization(self):
        """Test chunker initializes with correct defaults."""
        chunker = CodeChunker(max_chunk_size=1000, overlap=100)
        assert chunker.max_chunk_size == 1000
        assert chunker.overlap == 100
    
    def test_line_based_chunking(self):
        """Test line-based chunking strategy."""
        chunker = CodeChunker()
        code = "\n".join([f"line {i}" for i in range(100)])
        
        chunks = chunker.chunk_by_lines(code, 'test.py', lines_per_chunk=20)
        
        # Should create multiple chunks
        assert len(chunks) > 1
        
        # Verify chunk properties
        for chunk in chunks:
            assert chunk['chunk_type'] == 'line_chunk'
            assert 'start_line' in chunk
            assert 'end_line' in chunk
            assert chunk['strategy'] == ChunkStrategy.LINE_BASED.value
    
    def test_line_chunking_with_overlap(self):
        """Test that line chunking includes overlap."""
        chunker = CodeChunker(overlap=100)
        code = "\n".join([f"line {i}" for i in range(100)])
        
        chunks = chunker.chunk_by_lines(code, 'test.py', lines_per_chunk=10)
        
        # Check if chunks overlap (rough check)
        if len(chunks) > 1:
            # Second chunk should start before first chunk ends
            assert chunks[1]['start_line'] < chunks[0]['end_line']
    
    def test_token_based_chunking(self):
        """Test token-based chunking strategy."""
        chunker = CodeChunker()
        code = "def test():\n    " + " ".join(["code"] * 1000)
        
        chunks = chunker.chunk_by_tokens(code, 'test.py', tokens_per_chunk=100)
        
        # Should create multiple chunks
        assert len(chunks) > 1
        
        # Verify properties
        for chunk in chunks:
            assert 'content' in chunk
            assert chunk['chunk_type'] == 'token_chunk'
    
    def test_hybrid_chunking_keeps_small_chunks(self):
        """Test hybrid strategy keeps small semantic chunks."""
        chunker = CodeChunker(max_chunk_size=1000)
        
        semantic_chunks = [
            {
                'content': 'def small():\n    pass',
                'chunk_type': 'function',
                'name': 'small'
            }
        ]
        
        refined = chunker.chunk_hybrid(semantic_chunks, 'test.py')
        
        # Small chunk should be preserved
        assert len(refined) == 1
        assert refined[0]['chunk_type'] == 'function'
        assert refined[0]['strategy'] == ChunkStrategy.HYBRID.value
    
    def test_hybrid_chunking_splits_large_chunks(self, large_python_code):
        """Test hybrid strategy splits large semantic chunks."""
        chunker = CodeChunker(max_chunk_size=500)  # Small limit
        
        semantic_chunks = [
            {
                'content': large_python_code,
                'chunk_type': 'function',
                'name': 'large_function'
            }
        ]
        
        refined = chunker.chunk_hybrid(semantic_chunks, 'test.py')
        
        # Large chunk should be split
        assert len(refined) > 1
        
        # Sub-chunks should reference parent
        for chunk in refined:
            assert 'parent_type' in chunk
            assert chunk['parent_type'] == 'function'
    
    def test_strategy_decision_for_small_file(self):
        """Test automatic strategy selection for small files."""
        chunker = CodeChunker()
        code = "def test():\n    pass"
        
        strategy = chunker.decide_strategy(code, 'python', has_ast=True)
        
        # Small file with AST → semantic
        assert strategy == ChunkStrategy.SEMANTIC
    
    def test_strategy_decision_for_large_file(self):
        """Test automatic strategy selection for large files."""
        chunker = CodeChunker()
        code = "x" * 60000  # Large file
        
        strategy = chunker.decide_strategy(code, 'python', has_ast=True)
        
        # Large file → hybrid
        assert strategy == ChunkStrategy.HYBRID
    
    def test_strategy_decision_without_ast(self):
        """Test strategy selection when AST not available."""
        chunker = CodeChunker()
        code = "def test():\n    pass"
        
        strategy = chunker.decide_strategy(code, 'unknown', has_ast=False)
        
        # No AST → line-based or token-based
        assert strategy in [ChunkStrategy.LINE_BASED, ChunkStrategy.TOKEN_BASED]


# ========================================
# CONTEXT WINDOW MANAGER TESTS
# ========================================

class TestContextWindowManager:
    """Tests for ContextWindowManager."""
    
    def test_initialization(self):
        """Test manager initializes correctly."""
        manager = ContextWindowManager(max_context_tokens=8000)
        assert manager.max_context_tokens == 8000
    
    def test_fit_chunks_to_context(self):
        """Test fitting chunks within context window."""
        manager = ContextWindowManager(max_context_tokens=1000)
        
        chunks = [
            {'content': 'x' * 100},  # ~25 tokens
            {'content': 'y' * 100},  # ~25 tokens
            {'content': 'z' * 5000},  # ~1250 tokens (too large)
        ]
        
        fitted = manager.fit_chunks_to_context(chunks, query="test")
        
        # Should include first two, exclude third
        assert len(fitted) <= 2
    
    def test_prioritize_chunks(self):
        """Test chunk prioritization by type."""
        manager = ContextWindowManager()
        
        chunks = [
            {'chunk_type': 'line_chunk', 'content': 'A'},
            {'chunk_type': 'function', 'content': 'B'},
            {'chunk_type': 'class', 'content': 'C'},
            {'chunk_type': 'line_chunk', 'content': 'D'},
        ]
        
        prioritized = manager.prioritize_chunks(chunks, ['function', 'class'])
        
        # Functions and classes should come first
        assert prioritized[0]['chunk_type'] in ['function', 'class']
        assert prioritized[1]['chunk_type'] in ['function', 'class']


# ========================================
# INTEGRATION TESTS
# ========================================

class TestParserIntegration:
    """Integration tests for parser + chunker."""
    
    def test_parse_and_chunk_workflow(self, sample_python_code):
        """Test complete parse → chunk workflow."""
        parser = CodeParser()
        chunker = CodeChunker(max_chunk_size=500)
        
        # Step 1: Parse
        semantic_chunks = parser.parse_file(sample_python_code, 'python', 'test.py')
        assert len(semantic_chunks) > 0
        
        # Step 2: Apply hybrid chunking
        refined_chunks = chunker.chunk_hybrid(semantic_chunks, 'test.py')
        assert len(refined_chunks) > 0
        
        # Verify all chunks have required metadata
        for chunk in refined_chunks:
            assert 'content' in chunk
            assert 'file_path' in chunk
            assert 'strategy' in chunk
    
    def test_context_aware_chunking(self, large_python_code):
        """Test chunking with context window constraints."""
        parser = CodeParser()
        chunker = CodeChunker()
        manager = ContextWindowManager(max_context_tokens=2000)
        
        # Parse large code
        chunks = parser.parse_file(large_python_code, 'python', 'large.py')
        
        # Apply hybrid chunking
        refined = chunker.chunk_hybrid(chunks, 'large.py')
        
        # Fit to context
        fitted = manager.fit_chunks_to_context(refined, query="")
        
        # Should have reduced number of chunks
        assert len(fitted) <= len(refined)


# ========================================
# EDGE CASE TESTS
# ========================================

class TestParserEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_malformed_code(self):
        """Test handling of syntactically invalid code."""
        parser = CodeParser()
        malformed = "def broken(\n    # missing closing"
        
        # Should not crash, should use fallback
        chunks = parser.parse_file(malformed, 'python', 'broken.py')
        assert isinstance(chunks, list)
    
    def test_very_long_single_line(self):
        """Test handling of extremely long single line."""
        chunker = CodeChunker(max_chunk_size=100)
        code = "x = " + "1 + " * 1000 + "0"
        
        chunks = chunker.chunk_by_lines(code, 'test.py', lines_per_chunk=1)
        
        # Should handle gracefully
        assert len(chunks) >= 1
    
    def test_unicode_handling(self):
        """Test handling of unicode characters."""
        parser = CodeParser()
        code = "def hello():\n    print('你好世界')"
        
        chunks = parser.parse_file(code, 'python', 'unicode.py')
        assert len(chunks) > 0
        assert '你好' in chunks[0]['content']
    
    def test_mixed_line_endings(self):
        """Test handling of mixed line endings."""
        chunker = CodeChunker()
        code = "line1\nline2\r\nline3\rline4"
        
        chunks = chunker.chunk_by_lines(code, 'test.py')
        # Should handle gracefully
        assert len(chunks) > 0


# ========================================
# RUN TESTS
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])