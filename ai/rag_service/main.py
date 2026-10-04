"""
RAG Service - Medical Knowledge Retrieval-Augmented Generation.

Exposes:
  POST /ingest - Ingest PubMed articles into vector store
  POST /search - Search for relevant medical literature
  GET /health - Health check endpoint
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from rag_service.config import RAGConfig, validate_env
from rag_service.embedding_service import EmbeddingService
from rag_service.pubmed_client import PubMedClient
from rag_service.vector_store import VectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager for RAG service."""
    validate_env()
    logger.info("RAG Service starting up")
    yield
    logger.info("RAG Service shutting down")


app = FastAPI(
    title="BreastGuard AI - RAG Service",
    version="2.1.0",
    description="Medical knowledge retrieval and literature search service",
    lifespan=lifespan
)

# Initialize services
config = RAGConfig()
embedding_service = EmbeddingService(config)
vector_store = VectorStore(config, embedding_service)
pubmed_client = PubMedClient(config)


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    """Request body for article ingestion."""
    query: str = Field(..., description="PubMed search query")
    max_results: int = Field(default=50, description="Maximum articles to ingest")
    days_back: int = Field(default=365, description="Days to look back for articles")
    chunk_text: bool = Field(default=True, description="Whether to chunk long texts")


class IngestResponse(BaseModel):
    """Response for article ingestion."""
    status: str
    articles_fetched: int
    chunks_added: int
    query: str


class SearchRequest(BaseModel):
    """Request body for literature search."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=5, description="Number of results to return")
    min_similarity: float = Field(default=0.7, description="Minimum similarity threshold")


class SearchResult(BaseModel):
    """Single search result."""
    pmid: str
    title: str
    journal: str
    publication_date: str
    doi: Optional[str]
    similarity: float
    text: str
    metadata: dict


class SearchResponse(BaseModel):
    """Response for literature search."""
    query: str
    results: List[SearchResult]
    total_found: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/ingest")
async def ingest_articles(body: IngestRequest) -> JSONResponse:
    """
    Ingest PubMed articles into the vector store.
    
    Searches PubMed for articles matching the query, fetches their details,
    generates embeddings, and stores them in ChromaDB for retrieval.
    """
    try:
        logger.info(f"Ingestion request: query='{body.query}', max_results={body.max_results}")
        
        # Search PubMed
        pmids = pubmed_client.search_articles(
            query=body.query,
            max_results=body.max_results,
            days_back=body.days_back
        )
        
        if not pmids:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "no_articles",
                    "articles_fetched": 0,
                    "chunks_added": 0,
                    "query": body.query
                }
            )
        
        # Fetch article details
        articles = pubmed_client.fetch_articles(pmids)
        
        if not articles:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "fetch_failed",
                    "articles_fetched": 0,
                    "chunks_added": 0,
                    "query": body.query
                }
            )
        
        # Add to vector store
        chunks_added = vector_store.add_articles(
            articles=articles,
            chunk_text=body.chunk_text
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "articles_fetched": len(articles),
                "chunks_added": chunks_added,
                "query": body.query
            }
        )
        
    except Exception as e:
        logger.exception(f"Ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion error: {str(e)}"
        )


@app.post("/search")
async def search_literature(body: SearchRequest) -> JSONResponse:
    """
    Search for relevant medical literature.
    
    Performs semantic search over the ingested literature using
    vector similarity to find the most relevant articles.
    """
    try:
        logger.info(f"Search request: query='{body.query}', top_k={body.top_k}")
        
        # Override config threshold if specified
        original_threshold = config.similarity_threshold
        config.similarity_threshold = body.min_similarity
        
        # Perform search
        results = vector_store.search(
            query=body.query,
            top_k=body.top_k
        )
        
        # Restore original threshold
        config.similarity_threshold = original_threshold
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(SearchResult(
                pmid=result["pmid"],
                title=result["title"],
                journal=result["journal"],
                publication_date=result["publication_date"],
                doi=result.get("doi"),
                similarity=result["similarity"],
                text=result["text"],
                metadata=result["metadata"]
            ))
        
        return JSONResponse(
            status_code=200,
            content={
                "query": body.query,
                "results": [r.dict() for r in formatted_results],
                "total_found": len(formatted_results)
            }
        )
        
    except Exception as e:
        logger.exception(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search error: {str(e)}"
        )


@app.post("/ingest/guidelines")
async def ingest_guidelines(max_results: int = 20) -> JSONResponse:
    """
    Ingest breast cancer clinical guidelines and reviews.
    
    Convenience endpoint to ingest high-quality clinical guidelines
    and review articles for breast cancer.
    """
    try:
        logger.info("Ingesting breast cancer guidelines")
        
        articles = pubmed_client.get_breast_cancer_guidelines(max_results=max_results)
        
        if not articles:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "no_articles",
                    "articles_fetched": 0,
                    "chunks_added": 0,
                    "query": "breast cancer guidelines"
                }
            )
        
        chunks_added = vector_store.add_articles(articles, chunk_text=True)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "articles_fetched": len(articles),
                "chunks_added": chunks_added,
                "query": "breast cancer guidelines"
            }
        )
        
    except Exception as e:
        logger.exception(f"Guideline ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Guideline ingestion error: {str(e)}"
        )


@app.post("/ingest/ajcc-staging")
async def ingest_ajcc_references(max_results: int = 10) -> JSONResponse:
    """
    Ingest AJCC staging references.
    
    Convenience endpoint to ingest AJCC staging documentation
    and references.
    """
    try:
        logger.info("Ingesting AJCC staging references")
        
        articles = pubmed_client.get_ajcc_staging_references(max_results=max_results)
        
        if not articles:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "no_articles",
                    "articles_fetched": 0,
                    "chunks_added": 0,
                    "query": "AJCC staging"
                }
            )
        
        chunks_added = vector_store.add_articles(articles, chunk_text=True)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "articles_fetched": len(articles),
                "chunks_added": chunks_added,
                "query": "AJCC staging"
            }
        )
        
    except Exception as e:
        logger.exception(f"AJCC reference ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AJCC reference ingestion error: {str(e)}"
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "rag-service",
        "version": config.service_version,
        "documents_in_store": vector_store.count()
    }


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": config.service_name,
        "version": config.service_version,
        "description": "Medical knowledge retrieval and literature search service",
        "endpoints": {
            "ingest": "POST /ingest - Ingest PubMed articles",
            "search": "POST /search - Search literature",
            "ingest_guidelines": "POST /ingest/guidelines - Ingest clinical guidelines",
            "ingest_ajcc": "POST /ingest/ajcc-staging - Ingest AJCC references",
            "health": "GET /health - Health check"
        }
    }
