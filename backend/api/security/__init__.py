"""
Security package for the breast tumor severity classifier backend.

Exports:
    EncryptionService  — AES-256-GCM envelope encryption
    KMSClient          — abstract KMS interface
    get_kms_client     — factory for the configured KMS provider
    EncryptedFileStorage — high-level encrypted file store
    TokenData          — parsed JWT claims
    decode_token       — low-level JWT decode helper
    require_auth       — FastAPI dependency: valid JWT required
    require_admin      — FastAPI dependency: admin role required
"""

from backend.security.auth import (
    TokenData,
    decode_token,
    require_admin,
    require_auth,
)
from backend.security.encryption import EncryptionService
from backend.security.kms import KMSClient, get_kms_client
from backend.security.storage import EncryptedFileStorage

__all__ = [
    "EncryptionService",
    "KMSClient",
    "get_kms_client",
    "EncryptedFileStorage",
    "TokenData",
    "decode_token",
    "require_auth",
    "require_admin",
]
