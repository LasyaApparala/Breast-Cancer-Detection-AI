"""RAG Service Configuration."""
import os
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class RAGConfig(BaseSettings):
    """Configuration for RAG service."""
    
    # Service
    service_name: str = "rag-service"
    service_version: str = "2.1.0"
    port: int = 8003
    host: str = "0.0.0.0"
    
    # Vector Database (ChromaDB)
    chroma_persist_directory: str = Field(
        default="./chroma_db",
        description="Directory for ChromaDB persistence"
    )
    chroma_collection_name: str = Field(
        default="medical_literature",
        description="Name of ChromaDB collection"
    )
    
    # PubMed/NCBI API
    ncbi_api_key: Optional[str] = Field(
        default=None,
        description="NCBI API key for higher rate limits"
    )
    ncbi_email: str = Field(
        default="research@breastguard.ai",
        description="Email required for NCBI API"
    )
    ncbi_tool: str = Field(
        default="BreastGuardAI",
        description="Tool name for NCBI API"
    )
    pubmed_max_results: int = Field(
        default=50,
        description="Maximum number of PubMed results per query"
    )
    
    # Embedding Model
    embedding_model_name: str = Field(
        default="dmis-lab/biobert-base-cased-v1.1",
        description="HuggingFace model for embeddings"
    )
    embedding_device: str = Field(
        default="cpu",
        description="Device for embedding model (cpu/cuda)"
    )
    embedding_batch_size: int = Field(
        default=32,
        description="Batch size for embedding generation"
    )
    
    # Retrieval
    top_k_retrieval: int = Field(
        default=5,
        description="Number of documents to retrieve"
    )
    similarity_threshold: float = Field(
        default=0.7,
        description="Minimum similarity score for retrieval"
    )
    
    # Chunking
    chunk_size: int = Field(
        default=512,
        description="Maximum token count per chunk"
    )
    chunk_overlap: int = Field(
        default=50,
        description="Token overlap between chunks"
    )
    
    # Cache
    enable_cache: bool = Field(
        default=True,
        description="Enable query result caching"
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Time-to-live for cache entries"
    )
    
    @field_validator("similarity_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        return v
    
    class Config:
        env_file = ".env"
        env_prefix = "RAG_"
        extra = "ignore"


def validate_env() -> None:
    """Validate required environment variables."""
    config = RAGConfig()
    # Log configuration on startup
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"RAG Service configured: {config.service_name} v{config.service_version}")
    logger.info(f"ChromaDB persist directory: {config.chroma_persist_directory}")
    logger.info(f"Embedding model: {config.embedding_model_name}")
