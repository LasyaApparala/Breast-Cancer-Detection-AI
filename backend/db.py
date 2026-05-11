"""Database engine and session management for the FastAPI backend."""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Read DATABASE_URL from environment; fail fast if missing so the service
# startup validation (Task 5) can catch it before any request is served.
DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

engine = create_engine(
    DATABASE_URL,
    # Use a connection pool suitable for a web service.
    pool_pre_ping=True,  # verify connections before use
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and ensures cleanup.

    Usage::

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
