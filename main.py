from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api.v1.router import api_router
from app.worker.utils.logging_config import setup_logging

# Setup logging at module load time (before app starts)
setup_logging(
    level=settings.LOG_LEVEL,
    log_file="logs/xmonitor-api.log",
    console=True
)

# Get logger for this module
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting up application...")
    await init_db()
    
    # Initialize WebSocket manager with Redis
    from app.services.websocket import manager
    await manager.connect_redis()
    
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} is ready!")

    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    if manager.redis_client:
        await manager.redis_client.close()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="XMonitor API - Intelligent Safety Monitoring Backend",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    # allow_origins=settings.allowed_origins_list,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/", tags=["health"])
async def root():
    """Root endpoint - health check"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "version": settings.APP_VERSION
    }


# Include API router
app.include_router(api_router, prefix="/api/v1")

# Add WebSocket route
from app.api.v1.endpoints.websocket import websocket_monitoring
app.add_websocket_route("/ws/monitoring", websocket_monitoring)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

