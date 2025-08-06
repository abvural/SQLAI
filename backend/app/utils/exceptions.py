"""
Custom exceptions for SQLAI application
"""
from typing import Optional, Dict, Any

class SQLAIException(Exception):
    """Base exception for SQLAI application"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "INTERNAL_ERROR"
        self.details = details or {}
        self.status_code = status_code
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }

class DatabaseConnectionError(SQLAIException):
    """Database connection related errors"""
    
    def __init__(self, message: str, database_id: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_CONNECTION_ERROR",
            details={"database_id": database_id} if database_id else {},
            status_code=503
        )

class SchemaAnalysisError(SQLAIException):
    """Schema analysis related errors"""
    
    def __init__(self, message: str, table: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="SCHEMA_ANALYSIS_ERROR",
            details={"table": table} if table else {},
            status_code=500
        )

class QueryGenerationError(SQLAIException):
    """Query generation related errors"""
    
    def __init__(self, message: str, natural_query: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="QUERY_GENERATION_ERROR",
            details={"natural_query": natural_query} if natural_query else {},
            status_code=400
        )

class QueryExecutionError(SQLAIException):
    """Query execution related errors"""
    
    def __init__(self, message: str, sql: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="QUERY_EXECUTION_ERROR",
            details={"sql": sql} if sql else {},
            status_code=500
        )

class ValidationError(SQLAIException):
    """Input validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={"field": field} if field else {},
            status_code=400
        )

class AuthenticationError(SQLAIException):
    """Authentication related errors"""
    
    def __init__(self, message: str):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401
        )

class AuthorizationError(SQLAIException):
    """Authorization related errors"""
    
    def __init__(self, message: str, resource: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details={"resource": resource} if resource else {},
            status_code=403
        )

class ResourceNotFoundError(SQLAIException):
    """Resource not found errors"""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} with id '{resource_id}' not found",
            error_code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id},
            status_code=404
        )

class ConfigurationError(SQLAIException):
    """Configuration related errors"""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details={"config_key": config_key} if config_key else {},
            status_code=500
        )

class RateLimitError(SQLAIException):
    """Rate limiting errors"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after} if retry_after else {},
            status_code=429
        )

class TimeoutError(SQLAIException):
    """Operation timeout errors"""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="TIMEOUT_ERROR",
            details={"operation": operation} if operation else {},
            status_code=504
        )

class CacheError(SQLAIException):
    """Cache related errors"""
    
    def __init__(self, message: str, cache_key: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="CACHE_ERROR",
            details={"cache_key": cache_key} if cache_key else {},
            status_code=500
        )

class AIModelError(SQLAIException):
    """AI model related errors"""
    
    def __init__(self, message: str, model_name: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="AI_MODEL_ERROR",
            details={"model_name": model_name} if model_name else {},
            status_code=500
        )