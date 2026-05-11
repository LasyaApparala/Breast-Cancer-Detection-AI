import logging
import os
import sys

logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_PUBLIC_KEY_PATH",
    "KMS_PROVIDER",
    "ALLOWED_ORIGINS",
    "ML_SERVICE_URL",
    "DOCUMENT_PARSER_URL",
]


def validate_env() -> None:
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        logger.error(f"Missing required environment variables: {missing}")
        sys.exit(1)
