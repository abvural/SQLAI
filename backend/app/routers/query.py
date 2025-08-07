from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
import logging
import uuid

from app.utils.sql_validator import SQLValidator, SQLOperation, validate_user_input
from app.services.connection_pool import get_connection_pool_manager
from app.ai.query_builder import SQLQueryBuilder
from app.ai.nlp_processor import NLPProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query")

# NLP processor will be initialized per request with db_id

def _smart_user_query(name: str) -> str:
    """Smart user query - exact match if contains underscore, otherwise LIKE"""
    if '_' in name:
        # Full username with underscore - exact match
        return f"SELECT * FROM users WHERE username = '{name}'"
    else:
        # Partial name - use LIKE to find matching users
        return f"SELECT username, email FROM users WHERE username LIKE '%{name}%' LIMIT 10"

def _generate_smart_sql(prompt: str, db_id: str) -> tuple[str, float]:
    """Enhanced pattern-based SQL generation with better AI-like understanding"""
    import re
    prompt_lower = prompt.lower()
    
    # Advanced Turkish patterns with more variations
    patterns = [
        # User queries - multiple variations
        (r'(?:t[üu]m\s+)?kullan[ıi]c[ıi]lar?(?:\s+(?:listele|g[öo]ster))?', "SELECT * FROM users", 0.9),
        (r'(?:kaç|ka[çc])\s+kullan[ıi]c[ıi]', "SELECT COUNT(*) as user_count FROM users", 0.9),
        (r'kullan[ıi]c[ıi]\s+(?:say[ıi]s[ıi]|adet)', "SELECT COUNT(*) as user_count FROM users", 0.9),
        
        # Name-based filtering with more intelligence
        (r'(?:ismi|ad[ıi])\s+([a-zA-ZğüşıöçĞÜŞIÖÇ_]+)(?:\s+olan)?(?:\s+kullan[ıi]c[ıi]lar?)?', 
         lambda m: _smart_user_query(m.group(1).lower()), 0.9),
        
        # English patterns
        (r'(?:list\s+|show\s+|all\s+)?users?(?:\s+table)?', "SELECT * FROM users", 0.8),
        (r'(?:count|how\s+many)\s+users?', "SELECT COUNT(*) as user_count FROM users", 0.8),
        (r'users?\s+(?:named|with\s+name)\s+([a-zA-Z_]+)', 
         lambda m: _smart_user_query(m.group(1).lower()), 0.9),
        
        # Product queries
        (r'(?:t[üu]m\s+)?(?:[üu]r[üu]nler|products?)(?:\s+(?:listele|g[öo]ster))?', "SELECT * FROM products", 0.8),
        (r'(?:kaç|ka[çc])\s+(?:[üu]r[üu]n|product)', "SELECT COUNT(*) as product_count FROM products", 0.8),
        
        # Order queries  
        (r'(?:t[üu]m\s+)?(?:sipari[şs]ler?|orders?)(?:\s+(?:listele|g[öo]ster))?', "SELECT * FROM orders", 0.8),
        (r'(?:kaç|ka[çc])\s+(?:sipari[şs]|order)', "SELECT COUNT(*) as order_count FROM orders", 0.8),
        
        # Advanced queries
        (r'en\s+(?:çok|fazla)\s+sipari[şs]', "SELECT user_id, COUNT(*) as order_count FROM orders GROUP BY user_id ORDER BY order_count DESC LIMIT 10", 0.7),
        (r'toplam\s+(?:tutar|fiyat)', "SELECT SUM(total_amount) as total_sales FROM orders", 0.7),
    ]
    
    # Try each pattern
    for pattern_data in patterns:
        if len(pattern_data) == 3:
            pattern, sql_or_func, confidence = pattern_data
        else:
            pattern, sql_or_func = pattern_data
            confidence = 0.6
            
        match = re.search(pattern, prompt_lower)
        if match:
            if callable(sql_or_func):
                return sql_or_func(match), confidence
            else:
                return sql_or_func, confidence
    
    return None, 0.0

def _generate_simple_sql(prompt: str, db_id: str) -> tuple[str, float]:
    """Simple pattern-based SQL generation"""
    import re
    prompt_lower = prompt.lower()
    
    # Turkish name filtering patterns (using username field, supports underscores)
    name_patterns = [
        (r'ismi\s+([a-zA-ZğüşıöçĞÜŞIÖÇ_]+)\s+olan\s+kullan[ıi]c[ıi]lar', lambda m: f"SELECT * FROM users WHERE username = '{m.group(1).lower()}'"),
        (r'ad[ıi]\s+([a-zA-ZğüşıöçĞÜŞIÖÇ_]+)\s+olan\s+kullan[ıi]c[ıi]lar', lambda m: f"SELECT * FROM users WHERE username = '{m.group(1).lower()}'"),
        (r'ismi\s+([a-zA-ZğüşıöçĞÜŞIÖÇ_]+)', lambda m: f"SELECT * FROM users WHERE username = '{m.group(1).lower()}'"),
        (r'([a-zA-ZğüşıöçĞÜŞIÖÇ_]+)\s+isimli\s+kullan[ıi]c[ıi]lar', lambda m: f"SELECT * FROM users WHERE username = '{m.group(1).lower()}'"),
        (r'username.*([a-zA-ZğüşıöçĞÜŞIÖÇ_]+)', lambda m: f"SELECT * FROM users WHERE username = '{m.group(1).lower()}'"),
    ]
    
    # English name filtering patterns (using username field)  
    name_patterns.extend([
        # Exact match patterns for full usernames (with underscores)
        (r'users?\s+named\s+([a-zA-Z_]+)', lambda m: _smart_user_query(m.group(1).lower())),
        (r'users?\s+with\s+name\s+([a-zA-Z_]+)', lambda m: _smart_user_query(m.group(1).lower())),
        (r'users?\s+with\s+username\s+([a-zA-Z_]+)', lambda m: _smart_user_query(m.group(1).lower())),
        # LIKE pattern for partial matches
        (r'users?\s+containing\s+([a-zA-Z]+)', lambda m: f"SELECT username, email FROM users WHERE username LIKE '%{m.group(1).lower()}%' LIMIT 10"),
        (r'find\s+users?\s+([a-zA-Z]+)', lambda m: f"SELECT username, email FROM users WHERE username LIKE '%{m.group(1).lower()}%' LIMIT 10"),
    ])
    
    # General patterns
    general_patterns = [
        (r'kullan[ıi]c[ıi]lar.*listele|listele.*kullan[ıi]c[ıi]lar|t[üu]m\s+kullan[ıi]c[ıi]lar|kullan[ıi]c[ıi]\s+tablosu', "SELECT * FROM users"),
        (r'users?\s+table|list\s+users?|all\s+users?|show\s+users?', "SELECT * FROM users"),
        (r'ka[çc]\s+kullan[ıi]c[ıi]|kullan[ıi]c[ıi]\s+say[ıi]s[ıi]|kullan[ıi]c[ıi]\s+adet', "SELECT COUNT(*) as user_count FROM users"),
        (r'count\s+users?|how\s+many\s+users?|number\s+of\s+users?', "SELECT COUNT(*) as user_count FROM users"),
        (r'sipari[şs]ler|orders?', "SELECT * FROM orders"),
        (r'[üu]r[üu]nler|products?', "SELECT * FROM products"),
    ]
    
    # Check name patterns first (higher priority)
    for pattern, sql_func in name_patterns:
        match = re.search(pattern, prompt_lower)
        if match:
            if callable(sql_func):
                return sql_func(match), 0.9
            else:
                return sql_func, 0.9
    
    # Check general patterns
    for pattern, sql in general_patterns:
        if re.search(pattern, prompt_lower):
            return sql, 0.8
    
    return None, 0.0

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
async def natural_language_query(query: NaturalLanguageQuery, request: Request = None):
    """Process natural language query and convert to SQL"""
    query_id = str(uuid.uuid4())
    
    try:
        # Simple pattern-based SQL generation (fallback)
        # Print to console for real-time debugging
        print("=" * 60)
        print("🔍 NATURAL LANGUAGE QUERY DEBUG - FROM FRONTEND")
        print(f"📝 Received prompt: '{query.prompt}' (length: {len(query.prompt)})")
        print(f"🗄️ Database ID: {query.db_id}")
        print(f"⚡ Confidence threshold: {query.confidence_threshold}")
        if request:
            print(f"🌐 Client: {request.client}")
            print(f"🔗 URL: {request.url}")
        print("=" * 60)
        
        # Get schema info for better context
        schema_info = None
        try:
            from app.services.schema_analyzer import SchemaAnalyzer
            analyzer = SchemaAnalyzer()
            schema_info = analyzer.analyze_database_schema(query.db_id, deep_analysis=False)
        except Exception as e:
            logger.warning(f"Could not get schema info: {e}")
        
        # Initialize NLP processor with correct db_id for LLM integration
        print(f"🧠 Using Enhanced Turkish AI with LLM")
        nlp_processor = NLPProcessor(db_id=query.db_id)
        generated_sql, confidence = nlp_processor.generate_intelligent_sql(query.prompt, schema_info)
        
        print(f"🔧 Generated SQL: {generated_sql}")
        print(f"📊 LLM Confidence: {confidence}")
        print("=" * 60)
        
        if not generated_sql:
            return QueryResponse(
                query_id=query_id,
                status="failed",
                sql=None,
                confidence=confidence,
                results=None,
                row_count=None,
                execution_time=None,
                error="LLM could not generate SQL for this query. Please try rephrasing or use more specific terms."
            )
        
        # Check confidence threshold
        if confidence < query.confidence_threshold:
            return QueryResponse(
                query_id=query_id,
                status="low_confidence",
                sql=generated_sql,
                confidence=confidence,
                results=None,
                row_count=None,
                execution_time=None,
                error=f"Generated query confidence ({confidence:.2f}) below threshold ({query.confidence_threshold})"
            )
        
        # Execute the generated SQL
        pool_manager = get_connection_pool_manager()
        
        import time
        start_time = time.time()
        
        # Execute generated query
        results = pool_manager.execute_query(query.db_id, generated_sql)
        execution_time = time.time() - start_time
        
        # Convert results to list of dicts if needed
        if results and hasattr(results[0], '_asdict'):
            results = [dict(row._asdict()) for row in results]
        elif results and not isinstance(results[0], dict):
            results = [{"result": row} for row in results]
        
        return QueryResponse(
            query_id=query_id,
            status="completed",
            sql=generated_sql,
            confidence=confidence,
            results=results or [],
            row_count=len(results) if results else 0,
            execution_time=execution_time,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error in natural language query processing: {e}")
        return QueryResponse(
            query_id=query_id,
            status="error",
            sql=None,
            confidence=0.0,
            results=None,
            row_count=None,
            execution_time=None,
            error=str(e)
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

@router.get("/results/{query_id}")
async def get_query_results(query_id: str, offset: int = 0, limit: int = 1000):
    """Get query results by ID"""
    try:
        # Get query executor
        from app.services.query_executor import QueryExecutor
        executor = QueryExecutor()
        
        # Get query status
        status = executor.get_query_status(query_id)
        if not status:
            raise HTTPException(status_code=404, detail="Query not found")
        
        # If still running, return status
        if status['status'] == 'running':
            return {
                "status": "pending",
                "query_id": query_id,
                "progress": status.get('progress', 0),
                "rows_processed": status.get('rows_processed', 0)
            }
        
        # If completed, get results
        if status['status'] == 'completed':
            results = executor.get_query_results(query_id, offset, limit)
            if results:
                return {
                    "status": "completed",
                    "query_id": query_id,
                    "results": results['data'],
                    "row_count": results['total_rows'],
                    "execution_time": 0.1
                }
        
        # If failed, return error
        if status['status'] == 'failed':
            return {
                "status": "failed", 
                "query_id": query_id,
                "error": status.get('error', 'Unknown error')
            }
            
        raise HTTPException(status_code=404, detail="Query results not available")
        
    except Exception as e:
        logger.error(f"Error getting query results {query_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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