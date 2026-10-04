"""
AES-256-GCM envelope encryption for files and feature payloads.
Requirements: 8.1
"""
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionService:
    IV_SIZE = 12    # 96-bit nonce for GCM
    TAG_SIZE = 16   # 128-bit authentication tag
    KEY_SIZE = 32   # 256-bit key

    def generate_dek(self) -> bytes:
        """Generate a random 256-bit data encryption key."""
        return secrets.token_bytes(self.KEY_SIZE)

    def encrypt(self, plaintext: bytes, dek: bytes) -> tuple[bytes, bytes, bytes]:
        """
        Encrypt plaintext with AES-256-GCM.

        Returns:
            (iv, ciphertext, tag)
        """
        iv = secrets.token_bytes(self.IV_SIZE)
        aesgcm = AESGCM(dek)
        # AESGCM.encrypt returns ciphertext || auth_tag (tag appended)
        ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, None)
        ciphertext = ciphertext_with_tag[: -self.TAG_SIZE]
        tag = ciphertext_with_tag[-self.TAG_SIZE :]
        return iv, ciphertext, tag

    def decrypt(self, iv: bytes, ciphertext: bytes, tag: bytes, dek: bytes) -> bytes:
        """
        Decrypt AES-256-GCM ciphertext.

        Args:
            iv: 96-bit nonce used during encryption.
            ciphertext: Encrypted bytes (without tag).
            tag: 128-bit authentication tag.
            dek: 256-bit data encryption key.

        Returns:
            Original plaintext bytes.
        """
        aesgcm = AESGCM(dek)
        return aesgcm.decrypt(iv, ciphertext + tag, None)

    def pack(self, iv: bytes, ciphertext: bytes, tag: bytes) -> bytes:
        """Pack as IV || ciphertext || tag for storage."""
        return iv + ciphertext + tag

    def unpack(self, packed: bytes) -> tuple[bytes, bytes, bytes]:
        """Unpack stored bytes into (iv, ciphertext, tag)."""
        iv = packed[: self.IV_SIZE]
        tag = packed[-self.TAG_SIZE :]
        ciphertext = packed[self.IV_SIZE : -self.TAG_SIZE]
        return iv, ciphertext, tag
