"""
Encrypted file storage using AES-256-GCM envelope encryption.
Files are stored as IV || ciphertext || auth_tag.
DEKs are encrypted by the configured KMS provider before persistence.
Requirements: 8.1, 8.6
"""
import os
import uuid
from pathlib import Path

from backend.security.encryption import EncryptionService
from backend.security.kms import get_kms_client

_UPLOAD_BASE = Path(os.environ.get("UPLOAD_DIR", "./uploads"))


class EncryptedFileStorage:
    """
    Stores and retrieves files with AES-256-GCM envelope encryption.

    Usage::

        storage = EncryptedFileStorage()
        storage_path, encrypted_dek = storage.store(file_bytes, session_id)
        plaintext = storage.retrieve(storage_path, encrypted_dek)
    """

    def __init__(self):
        self._enc = EncryptionService()
        self._kms = get_kms_client()

    def store(self, file_bytes: bytes, session_id: str) -> tuple[str, bytes]:
        """
        Encrypt *file_bytes* and write to disk.

        Returns:
            (storage_path, encrypted_dek) — the caller must persist
            *encrypted_dek* alongside the document record so the file can
            be decrypted later.
        """
        dek = self._enc.generate_dek()
        iv, ciphertext, tag = self._enc.encrypt(file_bytes, dek)
        packed = self._enc.pack(iv, ciphertext, tag)

        document_id = str(uuid.uuid4())
        dest_dir = _UPLOAD_BASE / session_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / document_id
        dest_path.write_bytes(packed)

        encrypted_dek = self._kms.encrypt_dek(dek)
        return str(dest_path), encrypted_dek

    def retrieve(self, storage_path: str, encrypted_dek: bytes) -> bytes:
        """
        Decrypt and return the plaintext bytes for a previously stored file.

        Args:
            storage_path: Filesystem path returned by :meth:`store`.
            encrypted_dek: KMS-encrypted DEK returned by :meth:`store`.

        Returns:
            Original plaintext file bytes.
        """
        packed = Path(storage_path).read_bytes()
        iv, ciphertext, tag = self._enc.unpack(packed)
        dek = self._kms.decrypt_dek(encrypted_dek)
        return self._enc.decrypt(iv, ciphertext, tag, dek)
