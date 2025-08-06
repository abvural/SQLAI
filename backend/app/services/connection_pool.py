"""
Connection Pool Manager for handling multiple database connections efficiently
"""
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from contextlib import contextmanager
import threading
import psycopg2
from psycopg2 import pool
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.services.database_service import get_database_service

logger = logging.getLogger(__name__)

class ConnectionPoolManager:
    """Manages connection pools for multiple databases"""
    
    def __init__(self, db_service=None):
        """Initialize the connection pool manager"""
        self.pools: Dict[str, Engine] = {}
        self.psycopg_pools: Dict[str, pool.ThreadedConnectionPool] = {}
        self.pool_stats: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.db_service = db_service or get_database_service()
        
        # Pool configuration from settings
        self.pool_size = settings.pool_size
        self.max_overflow = settings.max_overflow
        self.pool_timeout = settings.pool_timeout
    
    def create_pool(self, conn_id: str) -> Engine:
        """
        Create a new connection pool for a database
        
        Args:
            conn_id: Connection ID from database service
            
        Returns:
            SQLAlchemy Engine with connection pool
        """
        with self.lock:
            # Check if pool already exists
            if conn_id in self.pools:
                logger.info(f"Pool already exists for {conn_id}")
                return self.pools[conn_id]
            
            # Get connection details
            conn_details = self.db_service.get_connection(conn_id)
            if not conn_details:
                raise ValueError(f"Connection {conn_id} not found")
            
            # Build connection URL
            connection_url = (
                f"postgresql://{conn_details['username']}:{conn_details['password']}"
                f"@{conn_details['host']}:{conn_details['port']}/{conn_details['database']}"
            )
            
            # Add SSL mode if specified
            if conn_details.get('ssl_mode') and conn_details['ssl_mode'] != 'disable':
                connection_url += f"?sslmode={conn_details['ssl_mode']}"
            
            # Create SQLAlchemy engine with connection pool
            engine = create_engine(
                connection_url,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_pre_ping=True,  # Verify connections before using
                echo=False,  # Set to True for SQL logging
                connect_args={
                    "connect_timeout": 10,
                    "options": "-c statement_timeout=30000"  # 30 second statement timeout
                }
            )
            
            # Test the connection
            try:
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    logger.info(f"Successfully created pool for {conn_details['name']} ({conn_id})")
            except Exception as e:
                logger.error(f"Failed to create pool for {conn_id}: {e}")
                engine.dispose()
                raise
            
            # Store the engine
            self.pools[conn_id] = engine
            
            # Initialize pool statistics
            self.pool_stats[conn_id] = {
                'created_at': datetime.utcnow(),
                'total_connections': 0,
                'active_connections': 0,
                'failed_connections': 0,
                'last_used': None
            }
            
            # Update database service status
            self.db_service.update_connection_status(conn_id, 'connected', datetime.utcnow())
            
            return engine
    
    def create_psycopg_pool(self, conn_id: str) -> pool.ThreadedConnectionPool:
        """
        Create a psycopg2 connection pool (alternative to SQLAlchemy)
        
        Args:
            conn_id: Connection ID
            
        Returns:
            psycopg2 ThreadedConnectionPool
        """
        with self.lock:
            if conn_id in self.psycopg_pools:
                return self.psycopg_pools[conn_id]
            
            conn_details = self.db_service.get_connection(conn_id)
            if not conn_details:
                raise ValueError(f"Connection {conn_id} not found")
            
            # Create psycopg2 connection pool
            conn_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.pool_size + self.max_overflow,
                host=conn_details['host'],
                port=conn_details['port'],
                database=conn_details['database'],
                user=conn_details['username'],
                password=conn_details['password'],
                sslmode=conn_details.get('ssl_mode', 'prefer'),
                connect_timeout=10
            )
            
            self.psycopg_pools[conn_id] = conn_pool
            logger.info(f"Created psycopg2 pool for {conn_details['name']} ({conn_id})")
            
            return conn_pool
    
    def get_engine(self, conn_id: str) -> Optional[Engine]:
        """
        Get SQLAlchemy engine for a connection
        
        Args:
            conn_id: Connection ID
            
        Returns:
            SQLAlchemy Engine or None
        """
        if conn_id not in self.pools:
            try:
                return self.create_pool(conn_id)
            except Exception as e:
                logger.error(f"Failed to get engine for {conn_id}: {e}")
                return None
        
        # Update last used time
        if conn_id in self.pool_stats:
            self.pool_stats[conn_id]['last_used'] = datetime.utcnow()
        
        return self.pools[conn_id]
    
    @contextmanager
    def get_connection(self, conn_id: str):
        """
        Context manager for getting a database connection
        
        Args:
            conn_id: Connection ID
            
        Yields:
            Database connection
        """
        engine = self.get_engine(conn_id)
        if not engine:
            raise ValueError(f"Could not get engine for {conn_id}")
        
        conn = None
        try:
            conn = engine.connect()
            
            # Update statistics
            if conn_id in self.pool_stats:
                self.pool_stats[conn_id]['total_connections'] += 1
                self.pool_stats[conn_id]['active_connections'] += 1
            
            yield conn
            
        except Exception as e:
            if conn_id in self.pool_stats:
                self.pool_stats[conn_id]['failed_connections'] += 1
            logger.error(f"Connection error for {conn_id}: {e}")
            raise
        finally:
            if conn:
                conn.close()
            if conn_id in self.pool_stats:
                self.pool_stats[conn_id]['active_connections'] -= 1
    
    @contextmanager
    def get_psycopg_connection(self, conn_id: str):
        """
        Context manager for getting a psycopg2 connection
        
        Args:
            conn_id: Connection ID
            
        Yields:
            psycopg2 connection
        """
        if conn_id not in self.psycopg_pools:
            self.create_psycopg_pool(conn_id)
        
        conn_pool = self.psycopg_pools[conn_id]
        conn = None
        
        try:
            conn = conn_pool.getconn()
            yield conn
        finally:
            if conn:
                conn_pool.putconn(conn)
    
    def execute_query(self, conn_id: str, query: str, params: Optional[Dict] = None) -> Any:
        """
        Execute a query on a specific database
        
        Args:
            conn_id: Connection ID
            query: SQL query
            params: Query parameters
            
        Returns:
            Query results
        """
        with self.get_connection(conn_id) as conn:
            result = conn.execute(text(query), params or {})
            if result.returns_rows:
                return result.fetchall()
            return result.rowcount
    
    def close_pool(self, conn_id: str):
        """
        Close and remove a connection pool
        
        Args:
            conn_id: Connection ID
        """
        with self.lock:
            # Close SQLAlchemy pool
            if conn_id in self.pools:
                self.pools[conn_id].dispose()
                del self.pools[conn_id]
                logger.info(f"Closed SQLAlchemy pool for {conn_id}")
            
            # Close psycopg2 pool
            if conn_id in self.psycopg_pools:
                self.psycopg_pools[conn_id].closeall()
                del self.psycopg_pools[conn_id]
                logger.info(f"Closed psycopg2 pool for {conn_id}")
            
            # Remove statistics
            if conn_id in self.pool_stats:
                del self.pool_stats[conn_id]
            
            # Update database service status
            self.db_service.update_connection_status(conn_id, 'disconnected')
    
    def close_all_pools(self):
        """Close all connection pools"""
        conn_ids = list(self.pools.keys()) + list(self.psycopg_pools.keys())
        for conn_id in set(conn_ids):
            self.close_pool(conn_id)
    
    def get_pool_statistics(self, conn_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get connection pool statistics
        
        Args:
            conn_id: Specific connection ID or None for all
            
        Returns:
            Pool statistics
        """
        if conn_id:
            if conn_id not in self.pool_stats:
                return {}
            
            stats = self.pool_stats[conn_id].copy()
            
            # Add SQLAlchemy pool info if available
            if conn_id in self.pools:
                engine = self.pools[conn_id]
                pool = engine.pool
                stats['pool_size'] = pool.size() if hasattr(pool, 'size') else 'N/A'
                stats['checked_out_connections'] = pool.checkedout() if hasattr(pool, 'checkedout') else 'N/A'
            
            return stats
        
        # Return all statistics
        all_stats = {}
        for cid in self.pool_stats:
            all_stats[cid] = self.get_pool_statistics(cid)
        return all_stats
    
    def health_check(self, conn_id: str) -> bool:
        """
        Check if a connection is healthy
        
        Args:
            conn_id: Connection ID
            
        Returns:
            True if healthy, False otherwise
        """
        try:
            result = self.execute_query(conn_id, "SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Health check failed for {conn_id}: {e}")
            return False
    
    def cleanup_idle_pools(self, idle_timeout_minutes: int = 30):
        """
        Clean up idle connection pools
        
        Args:
            idle_timeout_minutes: Minutes before considering a pool idle
        """
        current_time = datetime.utcnow()
        idle_threshold = timedelta(minutes=idle_timeout_minutes)
        
        pools_to_close = []
        
        for conn_id, stats in self.pool_stats.items():
            last_used = stats.get('last_used')
            if last_used and (current_time - last_used) > idle_threshold:
                if stats.get('active_connections', 0) == 0:
                    pools_to_close.append(conn_id)
        
        for conn_id in pools_to_close:
            logger.info(f"Closing idle pool: {conn_id}")
            self.close_pool(conn_id)
        
        return len(pools_to_close)

# Global instance
_connection_pool_manager: Optional[ConnectionPoolManager] = None

def get_connection_pool_manager() -> ConnectionPoolManager:
    """Get or create the global connection pool manager"""
    global _connection_pool_manager
    if _connection_pool_manager is None:
        _connection_pool_manager = ConnectionPoolManager()
    return _connection_pool_manager