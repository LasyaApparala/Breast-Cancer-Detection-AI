"""
JWT validation middleware and RBAC dependencies for FastAPI.
Requirements: 8.4, 8.5
"""
import os
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()


def get_public_key() -> str:
    """
    Load the RS256 public key.

    Checks JWT_PUBLIC_KEY_PATH first (file on disk), then falls back to the
    JWT_PUBLIC_KEY environment variable for local development.
    """
    key_path = os.environ.get("JWT_PUBLIC_KEY_PATH", "")
    if key_path and os.path.exists(key_path):
        with open(key_path) as f:
            return f.read()
    # Fallback for dev: use JWT_PUBLIC_KEY env var directly
    return os.environ.get("JWT_PUBLIC_KEY", "")


class TokenData:
    """Parsed claims extracted from a validated JWT."""

    def __init__(self, user_id: str, role: str):
        self.user_id = user_id
        self.role = role


def decode_token(token: str) -> TokenData:
    """
    Validate and decode a JWT bearer token.

    Raises:
        HTTPException 401: token is missing, expired, or otherwise invalid.
    """
    public_key = get_public_key()
    try:
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
        return TokenData(
            user_id=payload["sub"],
            role=payload.get("role", "user"),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    """
    FastAPI dependency that requires a valid JWT.

    Returns the decoded TokenData on success; raises HTTP 401 otherwise.
    """
    return decode_token(credentials.credentials)


async def require_admin(
    token_data: TokenData = Depends(require_auth),
) -> TokenData:
    """
    FastAPI dependency that requires the 'admin' role.

    Returns the decoded TokenData on success; raises HTTP 403 otherwise.
    """
    if token_data.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return token_data
