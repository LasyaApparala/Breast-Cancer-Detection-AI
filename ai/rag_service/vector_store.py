"""
Vector store management using ChromaDB.

Handles document storage, retrieval, and similarity search for
medical literature embeddings.
"""

import logging
from typing import Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings
from rag_service.config import RAGConfig
from rag_service.embedding_service import EmbeddingService
from rag_service.pubmed_client import PubMedArticle

logger = logging.getLogger(__name__)


class VectorStore:
    """
    ChromaDB-based vector store for medical literature.
    
    Manages document storage, metadata, and similarity search.
    """
    
    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        self.config = config or RAGConfig()
        self.embedding_service = embedding_service or EmbeddingService(self.config)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.config.chroma_persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.config.chroma_collection_name,
            metadata={"description": "Medical literature for BreastGuard AI"}
        )
        
        logger.info(f"Vector store initialized with {self.collection.count()} documents")
    
    def add_articles(
        self,
        articles: List[PubMedArticle],
        chunk_text: bool = True
    ) -> int:
        """
        Add articles to the vector store.
        
        Parameters
        ----------
        articles : List[PubMedArticle]
            List of PubMed articles to add
        chunk_text : bool
            Whether to chunk long texts before embedding
        
        Returns
        -------
        int
            Number of chunks added to the store
        """
        if not articles:
            return 0
        
        all_chunks = []
        all_embeddings = []
        all_metadatas = []
        all_ids = []
        
        for article in articles:
            # Combine title and abstract for embedding
            full_text = f"{article.title}\n\n{article.abstract}"
            
            if chunk_text:
                chunks = self._chunk_text(full_text)
            else:
                chunks = [full_text]
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{article.pmid}_chunk_{i}"
                
                # Generate embedding
                embedding = self.embedding_service.encode_single(chunk)
                
                # Prepare metadata
                metadata = {
                    "pmid": article.pmid,
                    "title": article.title,
                    "journal": article.journal,
                    "publication_date": article.publication_date,
                    "doi": article.doi or "",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "authors": ", ".join(article.authors[:5]),  # First 5 authors
                    "keywords": ", ".join(article.keywords[:10]),
                    "mesh_headings": ", ".join(article.mesh_headings[:10])
                }
                
                all_chunks.append(chunk)
                all_embeddings.append(embedding.tolist())
                all_metadatas.append(metadata)
                all_ids.append(chunk_id)
        
        # Add to ChromaDB
        if all_chunks:
            self.collection.add(
                documents=all_chunks,
                embeddings=all_embeddings,
                metadatas=all_metadatas,
                ids=all_ids
            )
            logger.info(f"Added {len(all_chunks)} chunks from {len(articles)} articles")
        
        return len(all_chunks)
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks for embedding.
        
        Uses simple token-based chunking with overlap.
        """
        # Approximate token count (rough estimate: 4 chars per token)
        chars_per_chunk = self.config.chunk_size * 4
        overlap_chars = self.config.chunk_overlap * 4
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chars_per_chunk
            chunk = text[start:end].strip()
            
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap_chars
        
        return chunks
    
    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar documents.
        
        Parameters
        ----------
        query : str
            Search query text
        top_k : int, optional
            Number of results to return (defaults to config value)
        filter_metadata : Dict, optional
            Metadata filters for the search
        
        Returns
        -------
        List[Dict]
            List of search results with metadata
        """
        if top_k is None:
            top_k = self.config.top_k_retrieval
        
        # Generate query embedding
        query_embedding = self.embedding_service.encode_single(query)
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=filter_metadata
        )
        
        # Format results
        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i]
                similarity = 1 - distance  # Convert distance to similarity
                metadata = results["metadatas"][0][i]
                
                if similarity >= self.config.similarity_threshold:
                    formatted_results.append({
                        "text": doc,
                        "similarity": similarity,
                        "metadata": metadata,
                        "pmid": metadata.get("pmid"),
                        "title": metadata.get("title"),
                        "journal": metadata.get("journal"),
                        "publication_date": metadata.get("publication_date"),
                        "doi": metadata.get("doi")
                    })
        
        logger.info(f"Search returned {len(formatted_results)} results above threshold")
        return formatted_results
    
    def get_by_pmid(self, pmid: str) -> List[Dict]:
        """
        Retrieve all chunks for a given PMID.
        
        Parameters
        ----------
        pmid : str
            PubMed ID to retrieve
        
        Returns
        -------
        List[Dict]
            List of document chunks
        """
        results = self.collection.get(
            where={"pmid": pmid}
        )
        
        formatted_results = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"]):
                formatted_results.append({
                    "text": doc,
                    "metadata": results["metadatas"][i]
                })
        
        return formatted_results
    
    def delete_by_pmid(self, pmid: str) -> int:
        """
        Delete all chunks for a given PMID.
        
        Parameters
        ----------
        pmid : str
            PubMed ID to delete
        
        Returns
        -------
        int
            Number of chunks deleted
        """
        # Get all IDs for this PMID
        results = self.collection.get(
            where={"pmid": pmid}
        )
        
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            logger.info(f"Deleted {len(results['ids'])} chunks for PMID {pmid}")
            return len(results["ids"])
        
        return 0
    
    def count(self) -> int:
        """Return total number of documents in the store."""
        return self.collection.count()
    
    def reset(self) -> None:
        """Clear all documents from the store."""
        self.client.delete_collection(name=self.config.chroma_collection_name)
        self.collection = self.client.create_collection(
            name=self.config.chroma_collection_name,
            metadata={"description": "Medical literature for BreastGuard AI"}
        )
        logger.warning("Vector store reset - all documents cleared")
