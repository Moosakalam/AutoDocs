"""
Unit tests for RAG components.
Tests vector store, retriever, and embeddings.
"""

import pytest
import tempfile
import shutil
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag.vector_store import VectorStore
from rag.retriever import CodeRetriever
from rag.embeddings import EmbeddingGenerator, EmbeddingCache, CodeEmbeddingProcessor


# ========================================
# FIXTURES
# ========================================

@pytest.fixture
def temp_db_dir():
    """Create temporary directory for ChromaDB."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        "def add(a, b): return a + b",
        "def subtract(a, b): return a - b",
        "class Calculator: pass"
    ]


@pytest.fixture
def sample_metadatas():
    """Sample metadata for testing."""
    return [
        {'file_path': 'math.py', 'chunk_type': 'function', 'language': 'python'},
        {'file_path': 'math.py', 'chunk_type': 'function', 'language': 'python'},
        {'file_path': 'calc.py', 'chunk_type': 'class', 'language': 'python'}
    ]


# ========================================
# VECTOR STORE TESTS
# ========================================

class TestVectorStore:
    """Tests for VectorStore."""
    
    def test_initialization(self, temp_db_dir):
        """Test vector store initializes correctly."""
        store = VectorStore(
            persist_directory=temp_db_dir,
            collection_name="test_collection"
        )
        
        assert store.collection is not None
        assert store.collection.name == "test_collection"
    
    def test_add_documents(self, temp_db_dir, sample_documents, sample_metadatas):
        """Test adding documents to vector store."""
        store = VectorStore(temp_db_dir, "test_collection")
        
        # Add documents
        store.add_documents(sample_documents, sample_metadatas)
        
        # Verify documents were added
        stats = store.get_collection_stats()
        assert stats['total_documents'] == 3
    
    def test_add_documents_with_embeddings(self, temp_db_dir, sample_documents, sample_metadatas):
        """Test adding documents with pre-computed embeddings."""
        store = VectorStore(temp_db_dir, "test_collection")
        
        # Create dummy embeddings (1536 dimensions)
        embeddings = [[0.1] * 1536 for _ in sample_documents]
        
        store.add_documents(sample_documents, sample_metadatas, embeddings)
        
        stats = store.get_collection_stats()
        assert stats['total_documents'] == 3
    
    def test_query_basic(self, temp_db_dir, sample_documents, sample_metadatas):
        """Test basic querying."""
        store = VectorStore(temp_db_dir, "test_collection")
        store.add_documents(sample_documents, sample_metadatas)
        
        # Query for addition-related code
        results = store.query("addition", n_results=2)
        
        assert 'documents' in results
        assert 'metadatas' in results
        assert 'distances' in results
        assert len(results['documents'][0]) <= 2
    
    def test_query_with_metadata_filter(self, temp_db_dir, sample_documents, sample_metadatas):
        """Test querying with metadata filters."""
        store = VectorStore(temp_db_dir, "test_collection")
        store.add_documents(sample_documents, sample_metadatas)
        
        # Query only for functions
        results = store.query(
            "math operation",
            n_results=5,
            filter_metadata={'chunk_type': 'function'}
        )
        
        # Should only return function chunks
        for metadata in results['metadatas'][0]:
            assert metadata['chunk_type'] == 'function'
    
    def test_deterministic_ids(self, temp_db_dir):
        """Test that same content generates same ID."""
        store = VectorStore(temp_db_dir, "test_collection")
        
        doc = "def test(): pass"
        metadata = {'file_path': 'test.py', 'chunk_index': 0}
        
        # Add same document twice
        store.add_documents([doc], [metadata])
        store.add_documents([doc], [metadata])
        
        # Should only have 1 document (not duplicated)
        stats = store.get_collection_stats()
        assert stats['total_documents'] == 1
    
    def test_reset_collection(self, temp_db_dir, sample_documents, sample_metadatas):
        """Test resetting collection."""
        store = VectorStore(temp_db_dir, "test_collection")
        store.add_documents(sample_documents, sample_metadatas)
        
        # Reset
        store.reset_collection()
        
        # Should be empty
        stats = store.get_collection_stats()
        assert stats['total_documents'] == 0
    
    def test_persistence(self, temp_db_dir, sample_documents, sample_metadatas):
        """Test that data persists across instances."""
        # Create store and add documents
        store1 = VectorStore(temp_db_dir, "test_collection")
        store1.add_documents(sample_documents, sample_metadatas)
        
        # Create new instance (should load persisted data)
        store2 = VectorStore(temp_db_dir, "test_collection")
        
        stats = store2.get_collection_stats()
        assert stats['total_documents'] == 3


# ========================================
# RETRIEVER TESTS
# ========================================

class TestCodeRetriever:
    """Tests for CodeRetriever."""
    
    def test_initialization(self, temp_db_dir):
        """Test retriever initializes correctly."""
        store = VectorStore(temp_db_dir, "test_collection")
        retriever = CodeRetriever(store)
        
        assert retriever.vector_store == store
    
    def test_retrieve_context_formatting(self, temp_db_dir, sample_documents, sample_metadatas):
        """Test that retrieval formats context properly."""
        store = VectorStore(temp_db_dir, "test_collection")
        store.add_documents(sample_documents, sample_metadatas)
        
        retriever = CodeRetriever(store)
        context = retriever.retrieve_context("addition", n_results=2)
        
        # Check formatting
        assert isinstance(context, str)
        assert 'Chunk' in context
        assert 'from' in context.lower()
        assert 'Relevance' in context
    
    def test_retrieve_context_includes_metadata(self, temp_db_dir, sample_documents, sample_metadatas):
        """Test that context includes metadata."""
        store = VectorStore(temp_db_dir, "test_collection")
        store.add_documents(sample_documents, sample_metadatas)
        
        retriever = CodeRetriever(store)
        context = retriever.retrieve_context("function")
        
        # Should include file path and type
        assert 'math.py' in context or 'calc.py' in context
        assert 'function' in context.lower() or 'class' in context.lower()
    
    def test_retrieve_by_file(self, temp_db_dir, sample_documents, sample_metadatas):
        """Test retrieving all chunks from specific file."""
        store = VectorStore(temp_db_dir, "test_collection")
        store.add_documents(sample_documents, sample_metadatas)
        
        retriever = CodeRetriever(store)
        chunks = retriever.retrieve_by_file('math.py')
        
        # Should get chunks from math.py
        assert len(chunks) >= 2
        for chunk in chunks:
            assert chunk['metadata']['file_path'] == 'math.py'
    
    def test_language_filtering(self, temp_db_dir):
        """Test filtering by programming language."""
        store = VectorStore(temp_db_dir, "test_collection")
        
        # Add mixed language documents
        docs = ["def py_func(): pass", "function jsFunc() {}"]
        metas = [
            {'file_path': 'test.py', 'language': 'python'},
            {'file_path': 'test.js', 'language': 'javascript'}
        ]
        store.add_documents(docs, metas)
        
        retriever = CodeRetriever(store)
        
        # Query with language filter
        context = retriever.retrieve_context("function", language_filter='python')
        
        # Should only include Python
        assert 'py_func' in context or 'python' in context.lower()


# ========================================
# EMBEDDING GENERATOR TESTS
# ========================================

class TestEmbeddingGenerator:
    """Tests for EmbeddingGenerator."""
    
    @patch('rag.embeddings.OpenAI')
    def test_openai_initialization(self, mock_openai):
        """Test OpenAI embedding initialization."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            generator = EmbeddingGenerator(provider="openai")
            assert generator.provider == "openai"
            assert generator.model == "text-embedding-3-small"
    
    @patch('rag.embeddings.SentenceTransformer')
    def test_sentence_transformer_initialization(self, mock_st):
        """Test sentence-transformers initialization."""
        generator = EmbeddingGenerator(
            provider="sentence_transformers",
            model="all-MiniLM-L6-v2"
        )
        assert generator.provider == "sentence_transformers"
    
    @patch('rag.embeddings.OpenAI')
    def test_generate_embeddings_openai(self, mock_openai):
        """Test OpenAI embedding generation."""
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536)
        ]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            generator = EmbeddingGenerator(provider="openai")
            generator.client = mock_client
            
            texts = ["text1", "text2"]
            embeddings = generator.generate_embeddings(texts)
            
            assert len(embeddings) == 2
            assert len(embeddings[0]) == 1536
    
    def test_get_embedding_dimension(self):
        """Test getting embedding dimensions."""
        # Can't test actual models without API, but test structure
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            with patch('rag.embeddings.OpenAI'):
                generator = EmbeddingGenerator(provider="openai", model="text-embedding-3-small")
                dim = generator.get_embedding_dimension()
                assert dim == 1536


# ========================================
# EMBEDDING CACHE TESTS
# ========================================

class TestEmbeddingCache:
    """Tests for EmbeddingCache."""
    
    def test_cache_initialization(self, tmp_path):
        """Test cache initializes correctly."""
        cache_file = tmp_path / "test_cache.json"
        cache = EmbeddingCache(cache_file=str(cache_file))
        
        assert cache.cache_file == str(cache_file)
        assert isinstance(cache.cache, dict)
    
    def test_cache_set_and_get(self, tmp_path):
        """Test caching and retrieving embeddings."""
        cache_file = tmp_path / "test_cache.json"
        cache = EmbeddingCache(cache_file=str(cache_file))
        
        embedding = [0.1, 0.2, 0.3]
        cache.set("hash123", embedding)
        
        retrieved = cache.get("hash123")
        assert retrieved == embedding
    
    def test_cache_persistence(self, tmp_path):
        """Test cache persists to disk."""
        cache_file = tmp_path / "test_cache.json"
        
        # Create cache and add item
        cache1 = EmbeddingCache(cache_file=str(cache_file))
        cache1.set("hash123", [0.1, 0.2, 0.3])
        
        # Create new cache instance (should load from disk)
        cache2 = EmbeddingCache(cache_file=str(cache_file))
        retrieved = cache2.get("hash123")
        
        assert retrieved == [0.1, 0.2, 0.3]
    
    def test_batch_operations(self, tmp_path):
        """Test batch get/set operations."""
        cache_file = tmp_path / "test_cache.json"
        cache = EmbeddingCache(cache_file=str(cache_file))
        
        # Batch set
        pairs = {
            "hash1": [0.1] * 10,
            "hash2": [0.2] * 10,
            "hash3": [0.3] * 10
        }
        cache.batch_set(pairs)
        
        # Batch get
        hashes = ["hash1", "hash2"]
        retrieved = cache.batch_get(hashes)
        
        assert len(retrieved) == 2
        assert "hash1" in retrieved
        assert "hash2" in retrieved


# ========================================
# CODE EMBEDDING PROCESSOR TESTS
# ========================================

class TestCodeEmbeddingProcessor:
    """Tests for CodeEmbeddingProcessor."""
    
    def test_preprocess_code(self):
        """Test code preprocessing."""
        processor = CodeEmbeddingProcessor(provider="openai", use_cache=False)
        
        code = "\n\n  def test():  \n    pass  \n\n"
        preprocessed = processor.preprocess_code(code)
        
        # Should remove leading/trailing empty lines and extra whitespace
        assert not preprocessed.startswith('\n')
        assert not preprocessed.endswith('\n\n')
    
    @patch('rag.embeddings.EmbeddingGenerator')
    def test_embed_code_chunks_without_cache(self, mock_generator_class):
        """Test embedding chunks without cache."""
        # Mock generator
        mock_generator = MagicMock()
        mock_generator.generate_embeddings.return_value = [
            [0.1] * 1536,
            [0.2] * 1536
        ]
        mock_generator_class.return_value = mock_generator
        
        processor = CodeEmbeddingProcessor(provider="openai", use_cache=False)
        processor.generator = mock_generator
        
        chunks = [
            {'content': 'def test1(): pass'},
            {'content': 'def test2(): pass'}
        ]
        
        result = processor.embed_code_chunks(chunks)
        
        # Should have embeddings
        assert all('embedding' in chunk for chunk in result)
        assert len(result[0]['embedding']) == 1536
    
    def test_preprocess_removes_excessive_whitespace(self):
        """Test that preprocessing handles whitespace correctly."""
        processor = CodeEmbeddingProcessor(provider="openai", use_cache=False)
        
        code = "def test():    \n    line1     \n    line2     "
        preprocessed = processor.preprocess_code(code)
        
        # Should remove trailing spaces from lines
        assert '    \n' not in preprocessed or preprocessed.count('    \n') < code.count('    \n')


# ========================================
# INTEGRATION TESTS
# ========================================

class TestRAGIntegration:
    """Integration tests for RAG components."""
    
    def test_full_rag_pipeline(self, temp_db_dir):
        """Test complete RAG pipeline: embed → store → retrieve."""
        # Step 1: Create embeddings (mock)
        chunks = [
            {'content': 'def add(a, b): return a + b', 'file_path': 'math.py', 'chunk_type': 'function'},
            {'content': 'def subtract(a, b): return a - b', 'file_path': 'math.py', 'chunk_type': 'function'}
        ]
        
        # Mock embeddings
        with patch('rag.embeddings.EmbeddingGenerator') as mock_gen_class:
            mock_gen = MagicMock()
            mock_gen.generate_embeddings.return_value = [[0.1] * 1536, [0.2] * 1536]
            mock_gen_class.return_value = mock_gen
            
            processor = CodeEmbeddingProcessor(provider="openai", use_cache=False)
            processor.generator = mock_gen
            
            # Add embeddings
            chunks_with_embeddings = processor.embed_code_chunks(chunks)
        
        # Step 2: Store in vector DB
        store = VectorStore(temp_db_dir, "test_collection")
        documents = [c['content'] for c in chunks_with_embeddings]
        metadatas = [{'file_path': c['file_path'], 'chunk_type': c['chunk_type']} 
                    for c in chunks_with_embeddings]
        embeddings = [c['embedding'] for c in chunks_with_embeddings]
        
        store.add_documents(documents, metadatas, embeddings)
        
        # Step 3: Retrieve
        retriever = CodeRetriever(store)
        context = retriever.retrieve_context("addition")
        
        # Verify end-to-end
        assert 'add' in context.lower() or 'subtract' in context.lower()
        assert 'math.py' in context


# ========================================
# EDGE CASE TESTS
# ========================================

class TestRAGEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_query(self, temp_db_dir, sample_documents, sample_metadatas):
        """Test handling of empty query."""
        store = VectorStore(temp_db_dir, "test_collection")
        store.add_documents(sample_documents, sample_metadatas)
        
        retriever = CodeRetriever(store)
        context = retriever.retrieve_context("", n_results=1)
        
        # Should handle gracefully
        assert isinstance(context, str)
    
    def test_query_on_empty_store(self, temp_db_dir):
        """Test querying empty vector store."""
        store = VectorStore(temp_db_dir, "test_collection")
        retriever = CodeRetriever(store)
        
        # Query empty store
        context = retriever.retrieve_context("test")
        
        # Should handle gracefully (empty or minimal response)
        assert isinstance(context, str)
    
    def test_very_long_document(self, temp_db_dir):
        """Test handling of very long documents."""
        store = VectorStore(temp_db_dir, "test_collection")
        
        # Very long document
        long_doc = "x" * 100000
        metadata = {'file_path': 'long.py', 'chunk_type': 'file'}
        
        # Should handle without crashing
        store.add_documents([long_doc], [metadata])
        
        stats = store.get_collection_stats()
        assert stats['total_documents'] == 1


# ========================================
# RUN TESTS
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])