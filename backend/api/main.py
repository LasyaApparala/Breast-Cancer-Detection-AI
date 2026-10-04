"""BreastGuard AI — FastAPI backend entry point."""
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import validate_env

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_env()
    # Auto-create all tables (SQLite dev or fresh Postgres)
    try:
        from backend.db import engine
        from backend.models.db_models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ready.")
    except Exception as e:
        logger.warning(f"Could not auto-create tables: {e}")
    yield


app = FastAPI(
    title="BreastGuard AI",
    version="2.1.0",
    description="Breast tumor severity classification API",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.routers.upload import upload_router
from backend.routers.classify import classify_router
from backend.routers.admin import admin_router

app.include_router(upload_router, prefix="/api/v1")
app.include_router(classify_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "backend"}
