"""
Document Parser microservice.

Exposes:
  POST /parse  — parse documents and extract clinical features
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from document_parser.config import validate_env
from document_parser.feature_extractor import FeatureExtractor
from document_parser.parser import DocumentParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_env()
    yield


app = FastAPI(lifespan=lifespan)

_parser = DocumentParser()
_extractor = FeatureExtractor()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ParseRequest(BaseModel):
    document_ids: list[str]
    session_id: str


# ---------------------------------------------------------------------------
# POST /parse
# ---------------------------------------------------------------------------

@app.post("/parse")
async def parse_documents(body: ParseRequest) -> JSONResponse:
    """
    Parse a list of documents and extract clinical features.

    For each document_id:
      1. Read the file from storage (plain file read; encryption integration
         is handled in Task 6.3).
      2. Parse the file bytes into a ParsedDocument.
      3. Extract clinical features using FeatureExtractor.

    Returns a merged feature dict (later documents override earlier ones for
    the same feature, unless the earlier value was already present).

    Requirements: 2.1, 2.2, 2.3
    """
    merged_features: dict[str, Any] = {}

    for document_id in body.document_ids:
        # Resolve storage path — documents are stored under a configurable
        # base directory, keyed by document_id.
        storage_base = os.environ.get("DOCUMENT_STORAGE_PATH", "/tmp/documents")
        doc_dir = os.path.join(storage_base, document_id)

        # Locate the file: look for any file inside the document directory
        file_path: str | None = None
        mime_type: str = "application/pdf"

        if os.path.isdir(doc_dir):
            for fname in os.listdir(doc_dir):
                candidate = os.path.join(doc_dir, fname)
                if os.path.isfile(candidate):
                    file_path = candidate
                    mime_type = _infer_mime_type(fname)
                    break
        else:
            # Fallback: treat document_id as a direct file path
            if os.path.isfile(document_id):
                file_path = document_id
                mime_type = _infer_mime_type(document_id)

        if file_path is None:
            logger.warning(
                "Document %s not found in storage; skipping.", document_id
            )
            continue

        try:
            with open(file_path, "rb") as fh:
                file_bytes = fh.read()
        except OSError as exc:
            logger.error("Failed to read document %s: %s", document_id, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read document '{document_id}': {exc}",
            )

        try:
            parsed = _parser.parse(file_bytes, mime_type, document_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            )

        features = _extractor.extract(parsed)

        # Merge: only fill in features not yet found in earlier documents
        for fname, fvalue in features.items():
            if fname not in merged_features:
                merged_features[fname] = fvalue
            elif merged_features[fname].get("source") == "missing" and fvalue.get("source") != "missing":
                merged_features[fname] = fvalue

    return JSONResponse(
        status_code=200,
        content={
            "session_id": body.session_id,
            "features": merged_features,
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_mime_type(filename: str) -> str:
    """Infer MIME type from file extension."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "application/pdf"
    elif lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    elif lower.endswith(".png"):
        return "image/png"
    elif lower.endswith((".tif", ".tiff")):
        return "image/tiff"
    # Default to PDF
    return "application/pdf"
