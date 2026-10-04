"""
PubMed/NCBI API Client for real-time medical literature retrieval.

Uses Biopython's Entrez module to query PubMed database and retrieve
breast cancer research articles, NCCN guidelines, and AJCC staging rules.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from Bio import Entrez, Medline
from rag_service.config import RAGConfig

logger = logging.getLogger(__name__)


@dataclass
class PubMedArticle:
    """Structured representation of a PubMed article."""
    pmid: str
    title: str
    abstract: str
    authors: List[str]
    journal: str
    publication_date: str
    doi: Optional[str] = None
    keywords: List[str] = None
    mesh_headings: List[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.mesh_headings is None:
            self.mesh_headings = []


class PubMedClient:
    """
    Client for interacting with NCBI PubMed API.
    
    Handles rate limiting, error recovery, and article retrieval.
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        
        # Configure Entrez with credentials
        Entrez.email = self.config.ncbi_email
        Entrez.tool = self.config.ncbi_tool
        if self.config.ncbi_api_key:
            Entrez.api_key = self.config.ncbi_api_key
        
        # Rate limiting: NCBI allows 3 requests/second without API key,
        # 10 requests/second with API key
        self.rate_limit_delay = 0.1 if self.config.ncbi_api_key else 0.34
        self.last_request_time = 0.0
    
    def _rate_limit(self) -> None:
        """Apply rate limiting between API calls."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def search_articles(
        self,
        query: str,
        max_results: Optional[int] = None,
        days_back: int = 365,
        use_mesh: bool = True
    ) -> List[str]:
        """
        Search PubMed for articles matching the query.
        
        Parameters
        ----------
        query : str
            PubMed search query (supports MeSH terms, Boolean operators)
        max_results : int, optional
            Maximum number of results to return
        days_back : int
            Only return articles published within this many days
        use_mesh : bool
            Whether to use MeSH terms in the query
        
        Returns
        -------
        List[str]
            List of PubMed IDs (PMIDs)
        """
        if max_results is None:
            max_results = self.config.pubmed_max_results
        
        # Add date filter to query
        date_cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
        date_query = f'({query}) AND ("{date_cutoff}"[Date - Publication] : "3000"[Date - Publication])'
        
        # Add MeSH terms if requested
        if use_mesh:
            date_query = f'({date_query}) AND (breast neoplasms[MeSH Terms] OR mammary neoplasms[MeSH Terms])'
        
        logger.info(f"Searching PubMed with query: {date_query}")
        
        try:
            self._rate_limit()
            handle = Entrez.esearch(
                db="pubmed",
                term=date_query,
                retmax=max_results,
                usehistory="y",
                sort="relevance"
            )
            record = Entrez.read(handle)
            handle.close()
            
            pmids = record.get("IdList", [])
            logger.info(f"Found {len(pmids)} articles")
            return pmids
            
        except Exception as e:
            logger.error(f"PubMed search failed: {e}")
            return []
    
    def fetch_articles(self, pmids: List[str]) -> List[PubMedArticle]:
        """
        Fetch detailed article information for given PMIDs.
        
        Parameters
        ----------
        pmids : List[str]
            List of PubMed IDs to fetch
        
        Returns
        -------
        List[PubMedArticle]
            List of structured article data
        """
        if not pmids:
            return []
        
        articles = []
        batch_size = 100  # NCBI allows up to 100 IDs per fetch
        
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            
            try:
                self._rate_limit()
                handle = Entrez.efetch(
                    db="pubmed",
                    id=batch,
                    rettype="medline",
                    retmode="text"
                )
                records = Medline.parse(handle)
                handle.close()
                
                for record in records:
                    article = self._parse_medline_record(record)
                    if article:
                        articles.append(article)
                        
            except Exception as e:
                logger.error(f"Failed to fetch batch {i//batch_size}: {e}")
                continue
        
        logger.info(f"Successfully fetched {len(articles)} articles")
        return articles
    
    def _parse_medline_record(self, record: dict) -> Optional[PubMedArticle]:
        """Parse a Medline record into a PubMedArticle."""
        try:
            pmid = record.get("PMID")
            if not pmid:
                return None
            
            title = record.get("TI", "")
            abstract = record.get("AB", "")
            
            # Parse authors
            authors = []
            if "AU" in record:
                authors = record["AU"]
            
            # Parse journal info
            journal = record.get("TA", record.get("JT", ""))
            
            # Parse publication date
            pub_date = record.get("DP", record.get("EDAT", ""))
            
            # Parse DOI
            doi = record.get("AID", "")
            if doi and "[doi]" in doi:
                doi = doi.replace("[doi]", "").strip()
            elif "doi" in doi.lower():
                doi = doi.split()[-1].strip()
            else:
                doi = None
            
            # Parse keywords
            keywords = []
            if "OT" in record:
                keywords = record["OT"]
            elif "KW" in record:
                keywords = record["KW"]
            
            # Parse MeSH headings
            mesh_headings = []
            if "MH" in record:
                mesh_headings = record["MH"]
            
            return PubMedArticle(
                pmid=pmid,
                title=title,
                abstract=abstract,
                authors=authors,
                journal=journal,
                publication_date=pub_date,
                doi=doi,
                keywords=keywords,
                mesh_headings=mesh_headings
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse Medline record: {e}")
            return None
    
    def get_breast_cancer_guidelines(
        self,
        max_results: int = 20
    ) -> List[PubMedArticle]:
        """
        Fetch recent breast cancer clinical guidelines and reviews.
        
        Parameters
        ----------
        max_results : int
            Maximum number of guidelines to retrieve
        
        Returns
        -------
        List[PubMedArticle]
            List of guideline articles
        """
        query = """
        (breast cancer[Title/Abstract] OR breast neoplasms[MeSH]) 
        AND (guideline[Title/Abstract] OR practice guideline[Publication Type] 
        OR consensus[Title/Abstract] OR review[Publication Type])
        AND (clinical[Title/Abstract] OR treatment[Title/Abstract] OR staging[Title/Abstract])
        """
        
        pmids = self.search_articles(query, max_results=max_results, days_back=1825)
        return self.fetch_articles(pmids)
    
    def get_ajcc_staging_references(
        self,
        max_results: int = 10
    ) -> List[PubMedArticle]:
        """
        Fetch AJCC staging references.
        
        Parameters
        ----------
        max_results : int
            Maximum number of references to retrieve
        
        Returns
        -------
        List[PubMedArticle]
            List of AJCC staging articles
        """
        query = """
        (AJCC[Title/Abstract] OR "American Joint Committee on Cancer"[Title/Abstract])
        AND (staging[Title/Abstract] OR TNM[Title/Abstract])
        AND (breast[Title/Abstract] OR mammary[Title/Abstract])
        """
        
        pmids = self.search_articles(query, max_results=max_results, days_back=3650)
        return self.fetch_articles(pmids)
