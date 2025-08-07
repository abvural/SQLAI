from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager
import uuid
import time
import json
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from app.config import settings
from app.routers import health, databases, schema, query, analytics, llm
from app.models import init_db
from app.utils.logging_config import setup_logging
from app.utils.error_handlers import register_exception_handlers
from app.websocket.manager import manager

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

# CORS middleware - Update to include all local development ports
cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3005",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3002"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time", "Content-Disposition", "X-Total-Count"]
)

app.include_router(health.router, prefix=settings.api_prefix, tags=["health"])
app.include_router(databases.router, prefix=settings.api_prefix, tags=["databases"])
app.include_router(schema.router, prefix=settings.api_prefix, tags=["schema"])
app.include_router(query.router, prefix=settings.api_prefix, tags=["query"])

app.include_router(llm.router, prefix=settings.api_prefix, tags=["llm"])
app.include_router(analytics.router, prefix=settings.api_prefix, tags=["analytics"])

# WebSocket endpoint for chat
@app.websocket("/ws/chat/{db_id}")
async def websocket_chat_endpoint(websocket: WebSocket, db_id: str):
    """WebSocket endpoint for real-time chat interface"""
    logger.info(f"WebSocket connection attempt for db_id: {db_id}")
    
    # Connect to room
    await manager.connect(websocket, room_id=f"chat_{db_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                # Parse JSON message
                message = json.loads(data)
                
                # Handle message
                await manager.handle_message(websocket, f"chat_{db_id}", message)
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {data}")
                await manager.send_personal_message({
                    'type': 'error',
                    'message': 'Invalid message format'
                }, websocket)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for db_id: {db_id}")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# WebSocket endpoint for query monitoring
@app.websocket("/ws/monitor/{query_id}")
async def websocket_monitor_endpoint(websocket: WebSocket, query_id: str):
    """WebSocket endpoint for real-time query monitoring"""
    logger.info(f"WebSocket monitoring connection for query_id: {query_id}")
    
    # Connect to monitoring room
    await manager.connect(websocket, room_id=f"monitor_{query_id}")
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket monitoring disconnected for query_id: {query_id}")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket monitoring error: {e}")
        manager.disconnect(websocket)

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