"""
Embedding service for generating document embeddings.

Uses sentence-transformers with BioBERT/pubmed-bert for generating
high-quality medical text embeddings for vector similarity search.
"""

import logging
from typing import List, Union

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from rag_service.config import RAGConfig

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using biomedical language models.
    
    Supports batch processing and GPU acceleration.
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.model = None
        self.device = self.config.embedding_device
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the embedding model."""
        try:
            logger.info(f"Loading embedding model: {self.config.embedding_model_name}")
            self.model = SentenceTransformer(
                self.config.embedding_model_name,
                device=self.device
            )
            logger.info(f"Model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: Optional[int] = None,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Encode text(s) into embedding vectors.
        
        Parameters
        ----------
        texts : str or List[str]
            Text or list of texts to encode
        batch_size : int, optional
            Batch size for encoding (defaults to config value)
        show_progress : bool
            Whether to show progress bar for large batches
        
        Returns
        -------
        np.ndarray
            Embedding vectors of shape (n_texts, embedding_dim)
        """
        if self.model is None:
            raise RuntimeError("Embedding model not loaded")
        
        if isinstance(texts, str):
            texts = [texts]
        
        if batch_size is None:
            batch_size = self.config.embedding_batch_size
        
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=True  # L2 normalization for cosine similarity
            )
            return embeddings
        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            raise
    
    def encode_single(self, text: str) -> np.ndarray:
        """
        Encode a single text string.
        
        Parameters
        ----------
        text : str
            Text to encode
        
        Returns
        -------
        np.ndarray
            Embedding vector of shape (embedding_dim,)
        """
        return self.encode(text)[0]
    
    def compute_similarity(
        self,
        query_embedding: np.ndarray,
        document_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Compute cosine similarity between query and documents.
        
        Parameters
        ----------
        query_embedding : np.ndarray
            Query embedding vector
        document_embeddings : np.ndarray
            Document embedding vectors
        
        Returns
        -------
        np.ndarray
            Similarity scores
        """
        # Cosine similarity = dot product of normalized vectors
        return np.dot(document_embeddings, query_embedding)
    
    def get_embedding_dim(self) -> int:
        """Return the dimension of the embedding vectors."""
        if self.model is None:
            raise RuntimeError("Embedding model not loaded")
        return self.model.get_sentence_embedding_dimension()
