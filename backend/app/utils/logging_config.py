"""
Logging configuration for SQLAI application
"""
import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime

from app.config import settings

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, "extra"):
            log_obj.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj)

def get_logging_config() -> Dict[str, Any]:
    """
    Get logging configuration dictionary
    """
    log_level = settings.log_level.upper()
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                "()": JSONFormatter
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "default",
                "stream": "ext://sys.stdout"
            },
            "file_app": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "detailed",
                "filename": str(LOGS_DIR / "app.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8"
            },
            "file_error": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": str(LOGS_DIR / "error.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8"
            },
            "file_query": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": str(LOGS_DIR / "query.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8"
            },
            "file_security": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "WARNING",
                "formatter": "json",
                "filename": str(LOGS_DIR / "security.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8"
            }
        },
        "loggers": {
            # Application loggers
            "app": {
                "level": log_level,
                "handlers": ["console", "file_app", "file_error"],
                "propagate": False
            },
            "app.services": {
                "level": log_level,
                "handlers": ["console", "file_app", "file_error"],
                "propagate": False
            },
            "app.routers": {
                "level": log_level,
                "handlers": ["console", "file_app", "file_error"],
                "propagate": False
            },
            "app.utils": {
                "level": log_level,
                "handlers": ["console", "file_app", "file_error"],
                "propagate": False
            },
            "app.ai": {
                "level": log_level,
                "handlers": ["console", "file_app", "file_error"],
                "propagate": False
            },
            
            # Query logger
            "query": {
                "level": "INFO",
                "handlers": ["file_query"],
                "propagate": False
            },
            
            # Security logger
            "security": {
                "level": "WARNING",
                "handlers": ["file_security"],
                "propagate": False
            },
            
            # Third-party loggers
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console", "file_error"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["console", "file_app"],
                "propagate": False
            },
            "sqlalchemy.engine": {
                "level": "WARNING" if not settings.debug else "INFO",
                "handlers": ["console", "file_app"],
                "propagate": False
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "file_app", "file_error"]
        }
    }
    
    return config

def setup_logging():
    """
    Setup logging configuration
    """
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    # Get root logger
    logger = logging.getLogger()
    logger.info("Logging system initialized")
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"Logs directory: {LOGS_DIR}")
    
    # Log application startup info
    app_logger = logging.getLogger("app")
    app_logger.info(f"SQLAI Application starting...")
    app_logger.info(f"Debug mode: {settings.debug}")
    app_logger.info(f"Version: {settings.app_version}")

# Custom loggers for specific purposes
def get_query_logger():
    """Get logger for query operations"""
    return logging.getLogger("query")

def get_security_logger():
    """Get logger for security events"""
    return logging.getLogger("security")

def log_query_execution(
    database_id: str,
    natural_query: str,
    generated_sql: str,
    execution_time: float,
    row_count: int,
    status: str,
    error: str = None
):
    """
    Log query execution details
    """
    query_logger = get_query_logger()
    query_logger.info(
        "Query executed",
        extra={
            "database_id": database_id,
            "natural_query": natural_query,
            "generated_sql": generated_sql,
            "execution_time": execution_time,
            "row_count": row_count,
            "status": status,
            "error": error
        }
    )

def log_security_event(
    event_type: str,
    message: str,
    user_id: str = None,
    ip_address: str = None,
    details: Dict[str, Any] = None
):
    """
    Log security events
    """
    security_logger = get_security_logger()
    security_logger.warning(
        message,
        extra={
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details or {}
        }
    )

def log_database_connection(
    database_id: str,
    host: str,
    database: str,
    status: str,
    error: str = None
):
    """
    Log database connection attempts
    """
    logger = logging.getLogger("app.services")
    if status == "success":
        logger.info(
            f"Database connection successful",
            extra={
                "database_id": database_id,
                "host": host,
                "database": database
            }
        )
    else:
        logger.error(
            f"Database connection failed",
            extra={
                "database_id": database_id,
                "host": host,
                "database": database,
                "error": error
            }
        )

def log_schema_analysis(
    database_id: str,
    table_count: int,
    column_count: int,
    relationship_count: int,
    analysis_time: float
):
    """
    Log schema analysis results
    """
    logger = logging.getLogger("app.services")
    logger.info(
        f"Schema analysis completed",
        extra={
            "database_id": database_id,
            "table_count": table_count,
            "column_count": column_count,
            "relationship_count": relationship_count,
            "analysis_time": analysis_time
        }
    )