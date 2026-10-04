"""
File upload and ingestion routes.
Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models.db_models import Document
from backend.security.auth import TokenData, require_auth
from backend.security.storage import EncryptedFileStorage

upload_router = APIRouter()

# Accepted MIME types per Requirement 1.1
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "application/dicom",
}

# 50 MB in bytes per Requirement 1.2
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024

# Maximum documents per request per Requirement 1.4
MAX_DOCUMENTS = 10


@upload_router.post("/upload")
async def upload_documents(
    files: list[UploadFile],
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(require_auth),
) -> JSONResponse:
    """
    Accept up to 10 document uploads (PDF, JPEG, PNG, TIFF, DICOM).

    Validates:
    - Document count ≤ 10
    - MIME type is in the allowed set
    - File size ≤ 50 MB

    On success, encrypts each file, persists a Document record, and returns
    the list of document IDs and a new session ID within 5 seconds.
    """
    # Requirement 1.4 — reject if more than 10 documents
    if len(files) > MAX_DOCUMENTS:
        return JSONResponse(
            status_code=422,
            content={
                "error": "too_many_documents",
                "detail": (
                    f"Maximum 10 documents per request; received {len(files)}"
                ),
            },
        )

    # Read all file bytes upfront so we can validate size before storing
    file_contents: list[tuple[UploadFile, bytes]] = []
    for upload_file in files:
        content = await upload_file.read()
        file_contents.append((upload_file, content))

    # Validate each file — MIME type and size (Requirements 1.2, 1.3)
    for upload_file, content in file_contents:
        mime = upload_file.content_type or ""
        if mime not in ALLOWED_MIME_TYPES:
            return JSONResponse(
                status_code=422,
                content={
                    "error": "unsupported_format",
                    "detail": (
                        f"File '{upload_file.filename}' has unsupported type. "
                        "Accepted: PDF, JPEG, PNG, TIFF, DICOM"
                    ),
                },
            )
        if len(content) > MAX_FILE_SIZE_BYTES:
            return JSONResponse(
                status_code=422,
                content={
                    "error": "file_too_large",
                    "detail": (
                        f"File '{upload_file.filename}' exceeds 50 MB limit"
                    ),
                },
            )

    # All files are valid — create a session ID for this upload batch
    session_id = str(uuid.uuid4())
    storage = EncryptedFileStorage()
    document_ids: list[str] = []
    now = datetime.now(tz=timezone.utc)

    for upload_file, content in file_contents:
        # Encrypt and store the file (Requirement 8.1)
        storage_path, _encrypted_dek = storage.store(content, session_id)

        # Persist document record (Requirement 1.5)
        doc_id = uuid.uuid4()
        document = Document(
            document_id=doc_id,
            session_id=None,  # session not yet created; linked at classify time
            filename=upload_file.filename or "",
            mime_type=upload_file.content_type or "",
            storage_path=storage_path,
            uploaded_at=now,
        )
        db.add(document)
        document_ids.append(str(doc_id))

    db.commit()

    # Requirement 1.5 — return unique document IDs and session ID within 5 s
    return JSONResponse(
        status_code=200,
        content={
            "document_ids": document_ids,
            "session_id": session_id,
        },
    )
