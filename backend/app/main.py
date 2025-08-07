from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager
import uuid
import time
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from app.config import settings
from app.routers import health, databases, schema, query, analytics
from app.models import init_db
from app.utils.logging_config import setup_logging
from app.utils.error_handlers import register_exception_handlers

# Setup logging
setup_logging()
logger = logging.getLogger("app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API running on {settings.api_host}:{settings.api_port}")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    logger.info("Shutting down application...")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None
)

# Register exception handlers
register_exception_handlers(app)

# Middleware for request ID and logging
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Log request
    logger.info(
        f"Request started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else None
        }
    )
    
    # Process request and measure time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log response
    logger.info(
        f"Request completed",
        extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "process_time": process_time
        }
    )
    
    return response

# Security middleware (only in production)
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts.split(",") if hasattr(settings, 'allowed_hosts') and settings.allowed_hosts else ["*"]
    )

# Compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"]
)

app.include_router(health.router, prefix=settings.api_prefix, tags=["health"])
app.include_router(databases.router, prefix=settings.api_prefix, tags=["databases"])
app.include_router(schema.router, prefix=settings.api_prefix, tags=["schema"])
app.include_router(query.router, prefix=settings.api_prefix, tags=["query"])
app.include_router(analytics.router, prefix=settings.api_prefix, tags=["analytics"])

@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": f"http://{settings.api_host}:{settings.api_port}/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )