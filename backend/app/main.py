import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger
from app.core.database import engine
from app.models.base import Base
from app.core.redis import redis_client
from app.core.kafka import kafka_client
from app.core.qdrant import qdrant_client
from app.core.exceptions import AppException
from app.middleware.auth import AuthMiddleware, OrganizationContextMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    start_time = time.time()

    app.state.redis_client = redis_client
    app.state.kafka_client = kafka_client
    app.state.qdrant_client = qdrant_client

    try:
        await redis_client.connect()
        logger.info("Redis connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")

    try:
        await kafka_client.connect()
        logger.info("Kafka connected")
    except Exception as e:
        logger.error(f"Kafka connection failed: {e}")

    try:
        await qdrant_client.connect()
        logger.info("Qdrant connected")
    except Exception as e:
        logger.error(f"Qdrant connection failed: {e}")

    app.state.start_time = start_time
    yield

    await redis_client.disconnect()
    await kafka_client.disconnect()
    await qdrant_client.disconnect()
    await engine.dispose()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# Global middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(OrganizationContextMiddleware)


# Exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "error_code": exc.error_code,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "uptime_seconds": time.time() - app.state.start_time
        if hasattr(app.state, "start_time")
        else 0,
        "services": {
            "redis": "connected" if app.state.redis_client._client else "disconnected",
            "kafka": "connected" if app.state.kafka_client._producer else "disconnected",
            "qdrant": "connected" if app.state.qdrant_client._client else "disconnected",
        },
    }


@app.get("/ready")
async def readiness():
    return {"status": "ready"}


# Mount API
app.include_router(api_router, prefix="/api/v1")
