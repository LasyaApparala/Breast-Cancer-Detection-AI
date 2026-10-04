"""
JWT validation middleware and RBAC dependencies for FastAPI.
Requirements: 8.4, 8.5
"""
import os
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


class TokenData:
    def __init__(self, user_id: str, role: str, exp: Optional[int] = None):
        self.user_id = user_id
        self.role = role
        self.exp = exp


def get_public_key() -> str:
    key_path = os.environ.get("JWT_PUBLIC_KEY_PATH", "")
    if key_path and os.path.exists(key_path):
        with open(key_path) as f:
            return f.read()
    return os.environ.get("JWT_PUBLIC_KEY", "")


def get_private_key() -> str:
    key_path = os.environ.get("JWT_PRIVATE_KEY_PATH", "")
    if key_path and os.path.exists(key_path):
        with open(key_path) as f:
            return f.read()
    return os.environ.get("JWT_PRIVATE_KEY", "")


def _dev_bypass_enabled() -> bool:
    return os.environ.get("DEV_AUTH_BYPASS", "true").lower() == "true"


def decode_token(token: str) -> TokenData:
    """
    Decode and validate a bearer token.

    In dev mode (DEV_AUTH_BYPASS=true, the default), any token or 'dev-...'
    token grants admin access without signature verification.
    """
    if _dev_bypass_enabled():
        return TokenData(user_id=_DEV_USER_ID, role="admin")

    public_key = get_public_key() or "dev-secret"
    try:
        payload = jwt.decode(token, public_key, algorithms=["RS256", "HS256"])
        return TokenData(
            user_id=payload["sub"],
            role=payload.get("role", "user"),
            exp=payload.get("exp"),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> TokenData:
    """Require a valid JWT (or dev bypass)."""
    if _dev_bypass_enabled():
        return TokenData(user_id=_DEV_USER_ID, role="admin")
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_token(credentials.credentials)


async def require_admin(
    token_data: TokenData = Depends(require_auth),
) -> TokenData:
    """Require admin role."""
    if token_data.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return token_data


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
