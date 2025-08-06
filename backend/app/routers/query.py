from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
import logging
import uuid

from app.utils.sql_validator import SQLValidator, SQLOperation, validate_user_input
from app.services.connection_pool import get_connection_pool_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query")

class NaturalLanguageQuery(BaseModel):
    """Natural language query request"""
    prompt: str = Field(..., description="Natural language query", max_length=1000)
    db_id: str = Field(..., description="Target database ID")
    confidence_threshold: float = Field(default=0.7, description="Minimum confidence threshold")
    
    @validator('prompt')
    def validate_prompt(cls, v):
        if not v or not v.strip():
            raise ValueError("Prompt cannot be empty")
        # Check for potential injection in natural language
        dangerous = SQLValidator.detect_injection_patterns(v)
        if dangerous:
            raise ValueError(f"Potentially dangerous patterns detected: {', '.join(dangerous[:3])}")
        return v.strip()

class SQLQuery(BaseModel):
    """SQL query request"""
    sql: str = Field(..., description="SQL query to execute", max_length=100000)
    db_id: str = Field(..., description="Target database ID")
    limit: Optional[int] = Field(default=1000, ge=1, le=10000, description="Result limit")
    
    @validator('sql')
    def validate_sql(cls, v):
        if not v or not v.strip():
            raise ValueError("SQL query cannot be empty")
        
        # Validate SQL query for safety
        is_valid, error = SQLValidator.validate_query(v, allowed_operations=[SQLOperation.SELECT])
        if not is_valid:
            raise ValueError(f"Invalid SQL: {error}")
        
        return v.strip()

class QueryResponse(BaseModel):
    """Query response model"""
    query_id: str
    status: str
    sql: Optional[str]
    confidence: Optional[float]
    results: Optional[List[Dict[str, Any]]]
    row_count: Optional[int]
    execution_time: Optional[float]
    error: Optional[str]

class QueryProgress(BaseModel):
    """Query progress model"""
    query_id: str
    status: str
    progress: int
    message: str
    started_at: datetime
    estimated_completion: Optional[datetime]

@router.post("/natural", response_model=QueryResponse)
async def natural_language_query(query: NaturalLanguageQuery):
    """Process natural language query and convert to SQL"""
    query_id = str(uuid.uuid4())
    
    # TODO: Implement NLP processing
    return QueryResponse(
        query_id=query_id,
        status="pending",
        sql=None,
        confidence=None,
        results=None,
        row_count=None,
        execution_time=None,
        error=None
    )

@router.post("/suggest")
async def suggest_query(prompt: str, db_id: str):
    """Get SQL query suggestions based on prompt"""
    # TODO: Implement query suggestions
    return {
        "suggestions": [],
        "templates": [],
        "similar_queries": []
    }

@router.post("/execute", response_model=QueryResponse)
async def execute_query(query: SQLQuery, background_tasks: BackgroundTasks):
    """Execute SQL query with validation"""
    query_id = str(uuid.uuid4())
    
    try:
        # Get connection pool manager
        pool_manager = get_connection_pool_manager()
        
        # Execute query with parameterized approach
        import time
        start_time = time.time()
        
        # Execute query
        results = pool_manager.execute_query(query.db_id, query.sql)
        
        execution_time = time.time() - start_time
        
        # Convert results to list of dicts if needed
        if results and hasattr(results[0], '_asdict'):
            results = [dict(row._asdict()) for row in results]
        elif results and not isinstance(results[0], dict):
            results = [{"result": row} for row in results]
        
        # Apply limit
        if query.limit and results:
            results = results[:query.limit]
        
        return QueryResponse(
            query_id=query_id,
            status="completed",
            sql=query.sql,
            confidence=1.0,
            results=results,
            row_count=len(results) if results else 0,
            execution_time=execution_time,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        return QueryResponse(
            query_id=query_id,
            status="failed",
            sql=query.sql,
            confidence=1.0,
            results=None,
            row_count=None,
            execution_time=None,
            error=str(e)
        )

@router.put("/cancel/{query_id}")
async def cancel_query(query_id: str):
    """Cancel a running query"""
    # TODO: Implement query cancellation
    return {
        "query_id": query_id,
        "status": "cancelled",
        "message": "Query cancellation requested"
    }

@router.get("/progress/{query_id}", response_model=QueryProgress)
async def get_query_progress(query_id: str):
    """Get query execution progress"""
    # TODO: Implement progress tracking
    return QueryProgress(
        query_id=query_id,
        status="running",
        progress=0,
        message="Query in progress",
        started_at=datetime.utcnow(),
        estimated_completion=None
    )

@router.get("/history")
async def get_query_history(
    db_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get query execution history"""
    # TODO: Implement query history
    return {
        "total": 0,
        "queries": [],
        "limit": limit,
        "offset": offset
    }

@router.post("/export")
async def export_results(
    query_id: str,
    format: str = "csv"
):
    """Export query results in specified format"""
    if format not in ["csv", "excel", "json"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {format}"
        )
    
    # TODO: Implement export functionality
    return {
        "message": f"Export initiated for query {query_id}",
        "format": format,
        "download_url": None
    }