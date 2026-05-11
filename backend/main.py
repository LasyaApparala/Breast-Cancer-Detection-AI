import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.config import validate_env
from backend.routers.admin import admin_router
from backend.routers.classify import classify_router
from backend.routers.upload import upload_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_env()
    yield


app = FastAPI(lifespan=lifespan)

# Wire up all routers under /api/v1
app.include_router(upload_router, prefix="/api/v1")
app.include_router(classify_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
