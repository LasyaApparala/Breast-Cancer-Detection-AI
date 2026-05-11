"""
KMS client abstraction for DEK encryption/decryption.
Supports HashiCorp Vault transit engine, AWS KMS, and a local-dev XOR stub.
Requirements: 8.6
"""
import base64
import os
from abc import ABC, abstractmethod


class KMSClient(ABC):
    """Abstract interface for key management service operations."""

    @abstractmethod
    def encrypt_dek(self, dek: bytes) -> bytes:
        """Encrypt a data encryption key with the master key."""
        ...

    @abstractmethod
    def decrypt_dek(self, encrypted_dek: bytes) -> bytes:
        """Decrypt an encrypted data encryption key."""
        ...


class VaultKMSClient(KMSClient):
    """HashiCorp Vault transit engine KMS client."""

    def __init__(self):
        self.vault_addr = os.environ["VAULT_ADDR"]
        self.vault_token = os.environ["VAULT_TOKEN"]
        self.key_name = os.environ.get("VAULT_KEY_NAME", "classifier-dek")

    def encrypt_dek(self, dek: bytes) -> bytes:
        import hvac  # type: ignore[import]

        client = hvac.Client(url=self.vault_addr, token=self.vault_token)
        encoded = base64.b64encode(dek).decode()
        result = client.secrets.transit.encrypt_data(self.key_name, encoded)
        return result["data"]["ciphertext"].encode()

    def decrypt_dek(self, encrypted_dek: bytes) -> bytes:
        import hvac  # type: ignore[import]

        client = hvac.Client(url=self.vault_addr, token=self.vault_token)
        result = client.secrets.transit.decrypt_data(
            self.key_name, encrypted_dek.decode()
        )
        return base64.b64decode(result["data"]["plaintext"])


class AWSKMS(KMSClient):
    """AWS KMS client."""

    def __init__(self):
        import boto3  # type: ignore[import]

        self.key_id = os.environ["AWS_KMS_KEY_ID"]
        self.client = boto3.client("kms")

    def encrypt_dek(self, dek: bytes) -> bytes:
        resp = self.client.encrypt(KeyId=self.key_id, Plaintext=dek)
        return resp["CiphertextBlob"]

    def decrypt_dek(self, encrypted_dek: bytes) -> bytes:
        resp = self.client.decrypt(CiphertextBlob=encrypted_dek)
        return resp["Plaintext"]


class LocalDevKMSClient(KMSClient):
    """
    Local development only — XOR with a fixed master key.
    NOT for production use. Keys must never be stored in env vars in production.
    """

    def __init__(self):
        key_hex = os.environ.get("LOCAL_DEV_MASTER_KEY", "0" * 64)
        self.master_key = bytes.fromhex(key_hex)

    def encrypt_dek(self, dek: bytes) -> bytes:
        return bytes(a ^ b for a, b in zip(dek, self.master_key[: len(dek)]))

    def decrypt_dek(self, encrypted_dek: bytes) -> bytes:
        return bytes(
            a ^ b for a, b in zip(encrypted_dek, self.master_key[: len(encrypted_dek)])
        )


def get_kms_client() -> KMSClient:
    """
    Factory that returns the appropriate KMS client based on KMS_PROVIDER env var.
    Defaults to LocalDevKMSClient when KMS_PROVIDER is unset or 'local_dev'.
    """
    provider = os.environ.get("KMS_PROVIDER", "local_dev")
    if provider == "vault":
        return VaultKMSClient()
    elif provider == "aws_kms":
        return AWSKMS()
    else:
        return LocalDevKMSClient()
