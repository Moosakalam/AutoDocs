"""
Embedding generation and management for code chunks.
Supports multiple embedding providers (OpenAI, local models).
"""

from typing import List, Dict, Optional
import os
from enum import Enum


class EmbeddingProvider(Enum):
    """Available embedding providers."""
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    SENTENCE_TRANSFORMERS = "sentence_transformers"


class EmbeddingGenerator:
    """
    Generates embeddings for code chunks.
    Supports multiple providers and caching.
    """
    
    def __init__(self, provider: str = "openai", model: str = "text-embedding-3-small"):
        """
        Initialize embedding generator.
        
        Args:
            provider: Embedding provider (openai, huggingface, sentence_transformers)
            model: Model name for embeddings
        """
        self.provider = provider
        self.model = model
        self.client = None
        
        # Initialize provider-specific client
        if provider == "openai":
            self._init_openai()
        elif provider == "sentence_transformers":
            self._init_sentence_transformers()
        elif provider == "huggingface":
            self._init_huggingface()
    
    def _init_openai(self):
        """Initialize OpenAI embeddings client."""
        try:
            from openai import OpenAI
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            
            self.client = OpenAI(api_key=api_key)
            print(f"✅ OpenAI embeddings initialized (model: {self.model})")
            
        except ImportError:
            raise ImportError("Install OpenAI SDK: pip install openai")
    
    def _init_sentence_transformers(self):
        """Initialize local sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            
            print(f"⏳ Loading sentence-transformers model: {self.model}...")
            self.client = SentenceTransformer(self.model)
            print(f"✅ Local embeddings model loaded")
            
        except ImportError:
            raise ImportError("Install sentence-transformers: pip install sentence-transformers")
    
    def _init_huggingface(self):
        """Initialize HuggingFace embeddings."""
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            
            print(f"⏳ Loading HuggingFace model: {self.model}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model)
            self.client = AutoModel.from_pretrained(self.model)
            print(f"✅ HuggingFace model loaded")
            
        except ImportError:
            raise ImportError("Install transformers: pip install transformers torch")
    
    def generate_embeddings(self, texts: List[str], 
                          batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            batch_size: Batch size for processing
        
        Returns:
            List of embedding vectors
        """
        if self.provider == "openai":
            return self._generate_openai_embeddings(texts, batch_size)
        elif self.provider == "sentence_transformers":
            return self._generate_sentence_transformer_embeddings(texts, batch_size)
        elif self.provider == "huggingface":
            return self._generate_huggingface_embeddings(texts, batch_size)
    
    def _generate_openai_embeddings(self, texts: List[str], 
                                   batch_size: int) -> List[List[float]]:
        """
        Generate embeddings using OpenAI API.
        
        Args:
            texts: List of texts
            batch_size: Batch size (OpenAI supports up to 2048 texts per call)
        
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        
        # Process in batches to avoid API limits
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                
                # Extract embeddings from response
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
                print(f"  Embedded batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
                
            except Exception as e:
                print(f"  ⚠ Error embedding batch {i//batch_size + 1}: {e}")
                # Return zero vectors as fallback
                dim = 1536 if "3-small" in self.model else 1536
                all_embeddings.extend([[0.0] * dim for _ in batch])
        
        return all_embeddings
    
    def _generate_sentence_transformer_embeddings(self, texts: List[str],
                                                 batch_size: int) -> List[List[float]]:
        """
        Generate embeddings using sentence-transformers (local).
        
        Args:
            texts: List of texts
            batch_size: Batch size for encoding
        
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Encode batch
            batch_embeddings = self.client.encode(
                batch,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            # Convert numpy arrays to lists
            all_embeddings.extend([emb.tolist() for emb in batch_embeddings])
            
            print(f"  Embedded batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
        
        return all_embeddings
    
    def _generate_huggingface_embeddings(self, texts: List[str],
                                        batch_size: int) -> List[List[float]]:
        """
        Generate embeddings using HuggingFace transformers.
        
        Args:
            texts: List of texts
            batch_size: Batch size
        
        Returns:
            List of embedding vectors
        """
        import torch
        
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Tokenize
            encoded = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors='pt'
            )
            
            # Generate embeddings
            with torch.no_grad():
                outputs = self.client(**encoded)
                # Use [CLS] token embedding or mean pooling
                embeddings = outputs.last_hidden_state[:, 0, :].numpy()
            
            all_embeddings.extend([emb.tolist() for emb in embeddings])
            
            print(f"  Embedded batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
        
        return all_embeddings
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by current model.
        
        Returns:
            Embedding dimension
        """
        if self.provider == "openai":
            # OpenAI embedding dimensions
            dimensions = {
                "text-embedding-3-small": 1536,
                "text-embedding-3-large": 3072,
                "text-embedding-ada-002": 1536
            }
            return dimensions.get(self.model, 1536)
        
        elif self.provider == "sentence_transformers":
            # Get from model
            return self.client.get_sentence_embedding_dimension()
        
        elif self.provider == "huggingface":
            # Get from model config
            return self.client.config.hidden_size
        
        return 1536  # Default


class EmbeddingCache:
    """
    Cache for embeddings to avoid regenerating.
    Useful for incremental updates.
    """
    
    def __init__(self, cache_file: str = "embeddings_cache.json"):
        """
        Initialize embedding cache.
        
        Args:
            cache_file: Path to cache file
        """
        self.cache_file = cache_file
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Load cache from disk."""
        import json
        from pathlib import Path
        
        if Path(self.cache_file).exists():
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        """Save cache to disk."""
        import json
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f)
    
    def get(self, text_hash: str) -> Optional[List[float]]:
        """
        Get cached embedding.
        
        Args:
            text_hash: Hash of the text
        
        Returns:
            Cached embedding or None
        """
        return self.cache.get(text_hash)
    
    def set(self, text_hash: str, embedding: List[float]):
        """
        Cache an embedding.
        
        Args:
            text_hash: Hash of the text
            embedding: Embedding vector
        """
        self.cache[text_hash] = embedding
        self._save_cache()
    
    def batch_get(self, text_hashes: List[str]) -> Dict[str, List[float]]:
        """
        Get multiple cached embeddings.
        
        Args:
            text_hashes: List of text hashes
        
        Returns:
            Dictionary of hash -> embedding
        """
        return {h: self.cache[h] for h in text_hashes if h in self.cache}
    
    def batch_set(self, hash_embedding_pairs: Dict[str, List[float]]):
        """
        Cache multiple embeddings.
        
        Args:
            hash_embedding_pairs: Dictionary of hash -> embedding
        """
        self.cache.update(hash_embedding_pairs)
        self._save_cache()


class CodeEmbeddingProcessor:
    """
    High-level processor for code embeddings.
    Combines generation, caching, and preprocessing.
    """
    
    def __init__(self, provider: str = "openai", 
                 model: str = "text-embedding-3-small",
                 use_cache: bool = True):
        """
        Initialize code embedding processor.
        
        Args:
            provider: Embedding provider
            model: Model name
            use_cache: Whether to use caching
        """
        self.generator = EmbeddingGenerator(provider, model)
        self.cache = EmbeddingCache() if use_cache else None
    
    def preprocess_code(self, code: str) -> str:
        """
        Preprocess code before embedding.
        
        Args:
            code: Raw code text
        
        Returns:
            Preprocessed code
        """
        # Remove excessive whitespace
        lines = code.split('\n')
        lines = [line.rstrip() for line in lines]
        
        # Remove empty lines at start/end
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        return '\n'.join(lines)
    
    def embed_code_chunks(self, chunks: List[Dict],
                         batch_size: int = 32) -> List[Dict]:
        """
        Embed code chunks with caching.
        
        Args:
            chunks: List of code chunks
            batch_size: Batch size for embedding
        
        Returns:
            Chunks with embeddings added
        """
        import hashlib
        
        # Preprocess and hash texts
        texts = []
        hashes = []
        chunk_to_hash = {}
        
        for i, chunk in enumerate(chunks):
            preprocessed = self.preprocess_code(chunk['content'])
            text_hash = hashlib.md5(preprocessed.encode()).hexdigest()
            
            texts.append(preprocessed)
            hashes.append(text_hash)
            chunk_to_hash[i] = text_hash
        
        # Check cache
        embeddings_dict = {}
        if self.cache:
            cached = self.cache.batch_get(hashes)
            embeddings_dict.update(cached)
            print(f"  📦 Cache hit: {len(cached)}/{len(hashes)} embeddings")
        
        # Generate missing embeddings
        missing_indices = [i for i, h in enumerate(hashes) if h not in embeddings_dict]
        
        if missing_indices:
            missing_texts = [texts[i] for i in missing_indices]
            missing_hashes = [hashes[i] for i in missing_indices]
            
            print(f"  🔄 Generating {len(missing_texts)} new embeddings...")
            new_embeddings = self.generator.generate_embeddings(
                missing_texts, 
                batch_size
            )
            
            # Update cache
            for h, emb in zip(missing_hashes, new_embeddings):
                embeddings_dict[h] = emb
            
            if self.cache:
                self.cache.batch_set({
                    h: emb for h, emb in zip(missing_hashes, new_embeddings)
                })
        
        # Add embeddings to chunks
        for i, chunk in enumerate(chunks):
            chunk['embedding'] = embeddings_dict[chunk_to_hash[i]]
        
        return chunks


# Example usage patterns:
"""
# Basic OpenAI embeddings:
generator = EmbeddingGenerator(provider="openai", model="text-embedding-3-small")
embeddings = generator.generate_embeddings(["code chunk 1", "code chunk 2"])

# Local embeddings (no API cost):
generator = EmbeddingGenerator(
    provider="sentence_transformers",
    model="all-MiniLM-L6-v2"
)
embeddings = generator.generate_embeddings(["code chunk 1", "code chunk 2"])

# High-level processor with caching:
processor = CodeEmbeddingProcessor(provider="openai", use_cache=True)
chunks_with_embeddings = processor.embed_code_chunks(code_chunks)

# Get embedding dimension:
dim = generator.get_embedding_dimension()  # 1536 for text-embedding-3-small
"""