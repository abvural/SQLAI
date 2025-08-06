"""
Query API Routes
Natural language to SQL conversion and execution
"""
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import asyncio
from datetime import datetime

from app.services.query_executor import QueryExecutor
from app.ai.query_builder import SQLQueryBuilder
from app.services.database_service import get_database_service
from app.utils.exceptions import SQLAIException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/query", tags=["Query"])

# Global instances
query_executor = QueryExecutor()
query_builder = SQLQueryBuilder()
db_service = get_database_service()

class NaturalQueryRequest(BaseModel):
    """Natural language query request"""
    query: str
    database_id: str
    user_id: Optional[str] = None

class SQLExecuteRequest(BaseModel):
    """Direct SQL execution request"""
    sql: str
    database_id: str
    user_id: Optional[str] = None
    stream: bool = False

class QueryResponse(BaseModel):
    """Query response"""
    success: bool
    query_id: Optional[str] = None
    sql: Optional[str] = None
    confidence: Optional[float] = None
    message: Optional[str] = None
    error: Optional[str] = None

@router.post("/natural", response_model=QueryResponse)
async def execute_natural_query(request: NaturalQueryRequest):
    """
    Execute natural language query
    
    Converts natural language to SQL and executes it
    """
    try:
        logger.info(f"Processing natural query: {request.query}")
        
        # Build SQL from natural language
        result = query_builder.build_query(request.query, request.database_id)
        
        if not result['success']:
            if result.get('ambiguous'):
                return QueryResponse(
                    success=False,
                    message="Query is ambiguous. Please be more specific.",
                    error=result.get('message')
                )
            else:
                return QueryResponse(
                    success=False,
                    error=result.get('error', 'Failed to understand query')
                )
        
        # Execute the generated SQL
        query_id = await query_executor.execute_query_async(
            db_id=request.database_id,
            sql=result['sql'],
            user_id=request.user_id
        )
        
        return QueryResponse(
            success=True,
            query_id=query_id,
            sql=result['sql'],
            confidence=result['confidence'],
            message="Query submitted for execution"
        )
        
    except Exception as e:
        logger.error(f"Natural query execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute", response_model=QueryResponse)
async def execute_sql_query(request: SQLExecuteRequest):
    """
    Execute SQL query directly
    
    For users who want to run SQL directly
    """
    try:
        logger.info(f"Executing SQL query for database: {request.database_id}")
        
        if request.stream:
            # Return streaming response
            return StreamingResponse(
                _stream_query_results(request.database_id, request.sql),
                media_type="application/json"
            )
        else:
            # Regular execution
            query_id = await query_executor.execute_query_async(
                db_id=request.database_id,
                sql=request.sql,
                user_id=request.user_id
            )
            
            return QueryResponse(
                success=True,
                query_id=query_id,
                sql=request.sql,
                message="Query submitted for execution"
            )
            
    except Exception as e:
        logger.error(f"SQL query execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _stream_query_results(database_id: str, sql: str):
    """Stream query results as NDJSON"""
    try:
        async for chunk in query_executor.stream_query_results(database_id, sql):
            for row in chunk:
                yield json.dumps(row, default=str) + '\n'
    except Exception as e:
        yield json.dumps({"error": str(e)}) + '\n'

@router.get("/status/{query_id}")
async def get_query_status(query_id: str):
    """Get query execution status"""
    try:
        status = query_executor.get_query_status(query_id)
        if not status:
            raise HTTPException(status_code=404, detail="Query not found")
        
        return {
            "query_id": query_id,
            "status": status['status'],
            "progress": status['progress'],
            "rows_processed": status['rows_processed'],
            "start_time": status['start_time'].isoformat(),
            "error": status.get('error')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get query status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{query_id}")
async def get_query_results(query_id: str, 
                           offset: int = 0, 
                           limit: int = 1000):
    """Get query results with pagination"""
    try:
        results = query_executor.get_query_results(query_id, offset, limit)
        if not results:
            raise HTTPException(status_code=404, detail="Results not found")
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get query results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/cancel/{query_id}")
async def cancel_query(query_id: str):
    """Cancel a running query"""
    try:
        success = query_executor.cancel_query(query_id)
        if success:
            return {"message": f"Query {query_id} cancellation requested"}
        else:
            raise HTTPException(status_code=404, detail="Query not found or not running")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/{query_id}")
async def export_query_results(query_id: str, 
                              format: str = "csv"):
    """Export query results in various formats"""
    try:
        if format not in ["csv", "excel", "json"]:
            raise HTTPException(status_code=400, detail="Invalid format")
        
        data = query_executor.export_results(query_id, format)
        if not data:
            raise HTTPException(status_code=404, detail="Results not found")
        
        # Set appropriate content type and filename
        content_types = {
            "csv": "text/csv",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "json": "application/json"
        }
        
        extensions = {
            "csv": "csv",
            "excel": "xlsx", 
            "json": "json"
        }
        
        filename = f"query_results_{query_id}.{extensions[format]}"
        
        return Response(
            content=data,
            media_type=content_types[format],
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_query_history(user_id: Optional[str] = None, limit: int = 50):
    """Get query execution history"""
    try:
        history = query_executor.get_query_history(user_id, limit)
        return {"history": history}
        
    except Exception as e:
        logger.error(f"Failed to get query history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/progress/{query_id}")
async def query_progress_websocket(websocket: WebSocket, query_id: str):
    """WebSocket for real-time query progress"""
    await websocket.accept()
    
    try:
        while True:
            status = query_executor.get_query_status(query_id)
            if not status:
                await websocket.send_json({"error": "Query not found"})
                break
            
            # Send progress update
            await websocket.send_json({
                "query_id": query_id,
                "status": status['status'],
                "progress": status['progress'],
                "rows_processed": status['rows_processed'],
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Break if query is completed or failed
            if status['status'] in ['completed', 'failed', 'cancelled']:
                break
            
            # Wait before next update
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for query {query_id}")
    except Exception as e:
        logger.error(f"WebSocket error for query {query_id}: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass

@router.post("/validate")
async def validate_sql(sql: str):
    """Validate SQL query"""
    try:
        result = query_builder.validate_query(sql)
        return result
        
    except Exception as e:
        logger.error(f"SQL validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suggestions")
async def get_query_suggestions(database_id: str, partial_query: str = ""):
    """Get query suggestions based on schema"""
    try:
        # This would integrate with the NLP processor to provide suggestions
        # For now, return basic suggestions
        suggestions = [
            "Show all customers",
            "Count orders by status", 
            "Total revenue this month",
            "Top 10 products by sales"
        ]
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))