"""
Async Query Executor with Memory Management
Handles query execution, cancellation, and streaming
"""
import logging
import asyncio
import uuid
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from io import StringIO
import json

from app.services.connection_pool import ConnectionPoolManager
from app.utils.sql_validator import SQLValidator
from app.models import get_session, QueryHistory

logger = logging.getLogger(__name__)

class QueryExecutor:
    """Execute queries with memory management and cancellation support"""
    
    def __init__(self):
        """Initialize query executor"""
        self.pool_manager = ConnectionPoolManager()
        self.validator = SQLValidator()
        self.active_queries: Dict[str, Dict[str, Any]] = {}
        self.query_results: Dict[str, Any] = {}
        
        logger.info("Query Executor initialized")
    
    async def execute_query_async(self, db_id: str, sql: str, 
                                 user_id: Optional[str] = None,
                                 chunk_size: int = 10000) -> str:
        """
        Execute query asynchronously with streaming support
        
        Args:
            db_id: Database connection ID
            sql: SQL query to execute
            user_id: User ID for tracking
            chunk_size: Size of chunks for streaming
            
        Returns:
            Query ID for tracking
        """
        # Generate query ID
        query_id = str(uuid.uuid4())
        
        # Validate query
        is_valid, errors = self.validator.validate_query(sql)
        if not is_valid:
            raise ValueError(f"Invalid query: {', '.join(errors)}")
        
        if self.validator.contains_dangerous_patterns(sql):
            raise ValueError("Query contains potentially dangerous patterns")
        
        # Store query info
        self.active_queries[query_id] = {
            'db_id': db_id,
            'sql': sql,
            'user_id': user_id,
            'status': 'running',
            'start_time': datetime.utcnow(),
            'progress': 0,
            'rows_processed': 0,
            'total_rows': None,
            'cancelled': False,
            'error': None
        }
        
        # Start execution in background
        asyncio.create_task(self._execute_query_task(query_id, chunk_size))
        
        logger.info(f"Started query execution: {query_id}")
        return query_id
    
    async def _execute_query_task(self, query_id: str, chunk_size: int):
        """Background task to execute query"""
        query_info = self.active_queries[query_id]
        
        try:
            # Get connection from pool
            pool = self.pool_manager.get_pool(query_info['db_id'])
            conn = pool.connect()
            
            # Create cursor for streaming
            cursor = conn.connection.cursor(name=f'cursor_{query_id}', 
                                          cursor_factory=RealDictCursor)
            cursor.itersize = chunk_size
            
            # Execute query
            cursor.execute(query_info['sql'])
            
            # Process results in chunks
            results = []
            rows_processed = 0
            
            while True:
                # Check if cancelled
                if query_info['cancelled']:
                    logger.info(f"Query {query_id} cancelled by user")
                    break
                
                # Fetch chunk
                chunk = cursor.fetchmany(chunk_size)
                if not chunk:
                    break
                
                # Process chunk
                results.extend(chunk)
                rows_processed += len(chunk)
                
                # Update progress
                query_info['rows_processed'] = rows_processed
                query_info['progress'] = min(rows_processed / 100000, 0.99)  # Estimate
                
                # Memory management - limit results
                if len(results) > 100000:
                    logger.warning(f"Query {query_id} exceeded memory limit, truncating")
                    query_info['truncated'] = True
                    break
                
                # Allow other tasks to run
                await asyncio.sleep(0)
            
            # Close cursor and connection
            cursor.close()
            conn.close()
            
            # Store results
            if not query_info['cancelled']:
                self.query_results[query_id] = {
                    'data': results,
                    'row_count': len(results),
                    'truncated': query_info.get('truncated', False)
                }
                query_info['status'] = 'completed'
                query_info['progress'] = 1.0
            else:
                query_info['status'] = 'cancelled'
            
            # Save to history
            self._save_query_history(query_info)
            
        except Exception as e:
            logger.error(f"Query {query_id} failed: {e}")
            query_info['status'] = 'failed'
            query_info['error'] = str(e)
            
        finally:
            query_info['end_time'] = datetime.utcnow()
    
    def cancel_query(self, query_id: str) -> bool:
        """
        Cancel a running query
        
        Args:
            query_id: Query ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        if query_id in self.active_queries:
            query_info = self.active_queries[query_id]
            if query_info['status'] == 'running':
                query_info['cancelled'] = True
                logger.info(f"Cancellation requested for query {query_id}")
                return True
        return False
    
    def get_query_status(self, query_id: str) -> Optional[Dict[str, Any]]:
        """
        Get query execution status
        
        Args:
            query_id: Query ID
            
        Returns:
            Query status information
        """
        if query_id in self.active_queries:
            info = self.active_queries[query_id].copy()
            # Remove sensitive info
            info.pop('sql', None)
            return info
        return None
    
    def get_query_results(self, query_id: str, 
                         offset: int = 0, 
                         limit: int = 1000) -> Optional[Dict[str, Any]]:
        """
        Get query results with pagination
        
        Args:
            query_id: Query ID
            offset: Start offset
            limit: Number of rows to return
            
        Returns:
            Query results
        """
        if query_id in self.query_results:
            results = self.query_results[query_id]
            data = results['data'][offset:offset + limit]
            
            return {
                'data': data,
                'total_rows': results['row_count'],
                'offset': offset,
                'limit': limit,
                'truncated': results.get('truncated', False)
            }
        return None
    
    async def stream_query_results(self, db_id: str, sql: str, 
                                  chunk_size: int = 1000) -> AsyncGenerator[List[Dict], None]:
        """
        Stream query results for large datasets
        
        Args:
            db_id: Database connection ID
            sql: SQL query
            chunk_size: Size of each chunk
            
        Yields:
            Chunks of query results
        """
        # Validate query
        is_valid, errors = self.validator.validate_query(sql)
        if not is_valid:
            raise ValueError(f"Invalid query: {', '.join(errors)}")
        
        # Get connection
        pool = self.pool_manager.get_pool(db_id)
        conn = pool.connect()
        
        try:
            # Create streaming cursor
            cursor = conn.connection.cursor(name='stream_cursor', 
                                          cursor_factory=RealDictCursor)
            cursor.itersize = chunk_size
            cursor.execute(sql)
            
            # Stream results
            while True:
                chunk = cursor.fetchmany(chunk_size)
                if not chunk:
                    break
                    
                yield chunk
                await asyncio.sleep(0)  # Allow other tasks
                
        finally:
            cursor.close()
            conn.close()
    
    def export_results(self, query_id: str, format: str = 'csv') -> Optional[bytes]:
        """
        Export query results in various formats
        
        Args:
            query_id: Query ID
            format: Export format (csv, excel, json)
            
        Returns:
            Exported data as bytes
        """
        if query_id not in self.query_results:
            return None
        
        results = self.query_results[query_id]
        data = results['data']
        
        if not data:
            return None
        
        if format == 'csv':
            df = pd.DataFrame(data)
            output = StringIO()
            df.to_csv(output, index=False)
            return output.getvalue().encode('utf-8')
            
        elif format == 'excel':
            df = pd.DataFrame(data)
            output = StringIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Results')
            return output.getvalue().encode()
            
        elif format == 'json':
            return json.dumps(data, indent=2, default=str).encode('utf-8')
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _save_query_history(self, query_info: Dict[str, Any]):
        """Save query to history"""
        try:
            with get_session() as session:
                history = QueryHistory(
                    query_id=query_info.get('query_id'),
                    database_id=query_info['db_id'],
                    sql_query=query_info['sql'],
                    user_id=query_info.get('user_id'),
                    status=query_info['status'],
                    rows_affected=query_info.get('rows_processed', 0),
                    execution_time=(
                        (query_info.get('end_time', datetime.utcnow()) - 
                         query_info['start_time']).total_seconds()
                    ),
                    error_message=query_info.get('error')
                )
                session.add(history)
                session.commit()
        except Exception as e:
            logger.error(f"Failed to save query history: {e}")
    
    def get_query_history(self, user_id: Optional[str] = None, 
                         limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get query execution history
        
        Args:
            user_id: Filter by user ID
            limit: Maximum number of records
            
        Returns:
            List of query history records
        """
        with get_session() as session:
            query = session.query(QueryHistory)
            
            if user_id:
                query = query.filter_by(user_id=user_id)
            
            records = query.order_by(QueryHistory.created_at.desc()).limit(limit).all()
            
            return [
                {
                    'query_id': r.query_id,
                    'database_id': r.database_id,
                    'sql_query': r.sql_query[:100] + '...' if len(r.sql_query) > 100 else r.sql_query,
                    'status': r.status,
                    'rows_affected': r.rows_affected,
                    'execution_time': r.execution_time,
                    'created_at': r.created_at.isoformat(),
                    'error_message': r.error_message
                }
                for r in records
            ]
    
    def cleanup_old_results(self, max_age_hours: int = 24):
        """
        Clean up old query results from memory
        
        Args:
            max_age_hours: Maximum age of results to keep
        """
        current_time = datetime.utcnow()
        queries_to_remove = []
        
        for query_id, info in self.active_queries.items():
            if info.get('end_time'):
                age = (current_time - info['end_time']).total_seconds() / 3600
                if age > max_age_hours:
                    queries_to_remove.append(query_id)
        
        for query_id in queries_to_remove:
            self.active_queries.pop(query_id, None)
            self.query_results.pop(query_id, None)
        
        if queries_to_remove:
            logger.info(f"Cleaned up {len(queries_to_remove)} old query results")