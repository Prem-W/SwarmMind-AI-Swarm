"""
SwarmMind - Main Application Entry Point

FastAPI application with all routes, middleware, and lifecycle management.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import agents, auth, execution, workflows
from app.api.websocket.execution_ws import router as ws_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.exceptions import SwarmMindException
from app.core.logging import configure_logging, get_logger

settings = get_settings()
logger = get_logger(__name__)

# Configure logging on import
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info(
        "SwarmMind starting",
        version=settings.app_version,
        env=settings.app_env,
    )

    # Initialize database
    await init_db()

    logger.info("SwarmMind ready")
    yield

    # Shutdown
    logger.info("SwarmMind shutting down")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-Agent AI Swarm Platform - Scalable autonomous agent collaboration",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for SwarmMind exceptions
@app.exception_handler(SwarmMindException)
async def swarm_exception_handler(request, exc: SwarmMindException):
    """Handle SwarmMind exceptions consistently."""
    from app.core.exceptions import handle_swarm_exception

    http_exc = handle_swarm_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail,
    )


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


# API Routes
app.include_router(auth.router, prefix=f"{settings.api_v1_prefix}")
app.include_router(agents.router, prefix=f"{settings.api_v1_prefix}")
app.include_router(workflows.router, prefix=f"{settings.api_v1_prefix}")
app.include_router(execution.router, prefix=f"{settings.api_v1_prefix}")
app.include_router(ws_router, prefix=f"{settings.api_v1_prefix}")


# Root endpoint
@app.get("/")
async def root():
    """API root with basic information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Multi-Agent AI Swarm Platform",
        "documentation": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        workers=1 if settings.is_development else settings.workers,
    )
