from fastapi import APIRouter, status
from datetime import datetime
import psutil
import os

from app.config import settings

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production"
    }

@router.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check():
    """Detailed health check with system metrics"""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production",
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "process": {
                "pid": os.getpid(),
                "threads": psutil.Process(os.getpid()).num_threads()
            }
        },
        "config": {
            "debug": settings.debug,
            "log_level": settings.log_level,
            "pool_size": settings.pool_size,
            "max_overflow": settings.max_overflow
        }
    }