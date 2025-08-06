"""
Error handlers for FastAPI application
"""
import logging
import traceback
from typing import Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError
from psycopg2 import OperationalError as PsycopgOperationalError

from app.utils.exceptions import (
    SQLAIException,
    DatabaseConnectionError,
    QueryExecutionError,
    ValidationError
)

logger = logging.getLogger(__name__)

async def sqlai_exception_handler(request: Request, exc: SQLAIException) -> JSONResponse:
    """
    Handle custom SQLAI exceptions
    """
    logger.error(
        f"SQLAI Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "request_id": request.state.request_id if hasattr(request.state, "request_id") else None
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation errors
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"][1:]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"Validation error on {request.url.path}",
        extra={
            "errors": errors,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {"errors": errors}
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions
    """
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP_{exc.status_code}",
            "message": exc.detail
        }
    )

async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle SQLAlchemy database errors
    """
    error_code = "DATABASE_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "Database operation failed"
    details = {}
    
    if isinstance(exc, OperationalError):
        error_code = "DATABASE_CONNECTION_ERROR"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        message = "Database connection failed"
        details = {"error": str(exc.orig) if hasattr(exc, 'orig') else str(exc)}
    elif isinstance(exc, IntegrityError):
        error_code = "DATABASE_INTEGRITY_ERROR"
        status_code = status.HTTP_409_CONFLICT
        message = "Database integrity constraint violated"
        details = {"error": str(exc.orig) if hasattr(exc, 'orig') else str(exc)}
    else:
        details = {"error": str(exc)}
    
    logger.error(
        f"SQLAlchemy Exception: {error_code}",
        extra={
            "error_code": error_code,
            "details": details,
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc()
        }
    )
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_code,
            "message": message,
            "details": details
        }
    )

async def psycopg_exception_handler(request: Request, exc: PsycopgOperationalError) -> JSONResponse:
    """
    Handle psycopg2 operational errors
    """
    logger.error(
        f"Psycopg2 Operational Error",
        extra={
            "error": str(exc),
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "DATABASE_CONNECTION_ERROR",
            "message": "Database connection failed",
            "details": {"error": str(exc)}
        }
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unhandled exceptions
    """
    logger.error(
        f"Unhandled exception: {type(exc).__name__}",
        extra={
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc()
        }
    )
    
    # In development, include more details
    from app.config import settings
    if settings.debug:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {
                    "exception_type": type(exc).__name__,
                    "exception": str(exc),
                    "traceback": traceback.format_exc().split('\n')
                }
            }
        )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred"
        }
    )

def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app
    """
    from fastapi import FastAPI
    
    # Custom exceptions
    app.add_exception_handler(SQLAIException, sqlai_exception_handler)
    
    # FastAPI/Starlette exceptions
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # Database exceptions
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(PsycopgOperationalError, psycopg_exception_handler)
    
    # General exception handler (catches everything else)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers registered")