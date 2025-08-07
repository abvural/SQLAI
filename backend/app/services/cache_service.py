"""
Cache service for managing schema metadata and query history
"""
import logging
import hashlib
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models import (
    DatabaseInfo,
    TableCache,
    ColumnCache,
    RelationshipCache,
    QueryHistory,
    AIInsight,
    SchemaSnapshot,
    get_session
)

logger = logging.getLogger(__name__)

class CacheService:
    """Service for managing cache database operations"""
    
    @staticmethod
    def save_database_info(
        db_id: str,
        name: str,
        host: str,
        port: int,
        database: str,
        username: str
    ) -> DatabaseInfo:
        """
        Save or update database information
        
        Args:
            db_id: Database connection ID
            name: Database display name
            host: Database host
            port: Database port
            database: Database name
            username: Username
            
        Returns:
            DatabaseInfo object
        """
        with get_session() as session:
            db_info = session.query(DatabaseInfo).filter_by(id=db_id).first()
            
            if not db_info:
                db_info = DatabaseInfo(
                    id=db_id,
                    name=name,
                    host=host,
                    port=port,
                    database=database,
                    username=username
                )
                session.add(db_info)
            else:
                db_info.name = name
                db_info.host = host
                db_info.port = port
                db_info.database = database
                db_info.username = username
                db_info.updated_at = datetime.utcnow()
            
            session.commit()
            session.refresh(db_info)
            logger.info(f"Saved database info: {name} ({db_id})")
            
            # Create a dict to return (to avoid detached instance issues)
            result = {
                'id': db_info.id,
                'name': db_info.name,
                'host': db_info.host,
                'port': db_info.port,
                'database': db_info.database,
                'username': db_info.username
            }
            return result
    
    @staticmethod
    def save_table_metadata(
        db_id: str,
        tables: List[Dict[str, Any]]
    ) -> int:
        """
        Save table metadata to cache
        
        Args:
            db_id: Database connection ID
            tables: List of table metadata dictionaries
            
        Returns:
            Number of tables saved
        """
        with get_session() as session:
            # Clear existing tables for this database
            session.query(TableCache).filter_by(database_id=db_id).delete()
            
            count = 0
            for table_data in tables:
                table = TableCache(
                    database_id=db_id,
                    schema_name=table_data.get('schema', 'public'),
                    table_name=table_data['name'],
                    row_count=table_data.get('row_count'),
                    size_bytes=table_data.get('size_bytes'),
                    table_type=table_data.get('type', 'TABLE'),
                    description=table_data.get('description'),
                    column_count=len(table_data.get('columns', [])),
                    has_primary_key=table_data.get('has_primary_key', False)
                )
                session.add(table)
                
                # Save columns
                for col_data in table_data.get('columns', []):
                    column = ColumnCache(
                        table=table,
                        column_name=col_data['name'],
                        data_type=col_data['type'],
                        is_nullable=col_data.get('nullable', True),
                        column_default=col_data.get('default'),
                        is_primary_key=col_data.get('is_primary_key', False),
                        is_foreign_key=col_data.get('is_foreign_key', False),
                        is_unique=col_data.get('is_unique', False)
                    )
                    session.add(column)
                
                count += 1
            
            # Update database info
            db_info = session.query(DatabaseInfo).filter_by(id=db_id).first()
            if db_info:
                db_info.total_tables = count
                db_info.total_columns = session.query(ColumnCache).join(TableCache).filter(
                    TableCache.database_id == db_id
                ).count()
                db_info.last_analyzed = datetime.utcnow()
            
            session.commit()
            logger.info(f"Saved {count} tables for database {db_id}")
            return count
    
    @staticmethod
    def save_relationships(
        db_id: str,
        relationships: List[Dict[str, Any]]
    ) -> int:
        """
        Save relationship metadata to cache
        
        Args:
            db_id: Database connection ID
            relationships: List of relationship dictionaries
            
        Returns:
            Number of relationships saved
        """
        with get_session() as session:
            # Clear existing relationships
            session.query(RelationshipCache).filter_by(database_id=db_id).delete()
            
            count = 0
            for rel_data in relationships:
                relationship = RelationshipCache(
                    database_id=db_id,
                    from_schema=rel_data.get('from_schema', 'public'),
                    from_table=rel_data['from_table'],
                    from_column=rel_data['from_column'],
                    to_schema=rel_data.get('to_schema', 'public'),
                    to_table=rel_data['to_table'],
                    to_column=rel_data['to_column'],
                    relationship_type=rel_data.get('type', 'one-to-many'),
                    constraint_name=rel_data.get('constraint_name'),
                    on_delete=rel_data.get('on_delete'),
                    on_update=rel_data.get('on_update'),
                    is_inferred=rel_data.get('is_inferred', False)
                )
                session.add(relationship)
                count += 1
            
            # Update database info
            db_info = session.query(DatabaseInfo).filter_by(id=db_id).first()
            if db_info:
                db_info.total_relationships = count
            
            session.commit()
            logger.info(f"Saved {count} relationships for database {db_id}")
            return count
    
    @staticmethod
    def get_tables(db_id: str, schema: str = 'public') -> List[Dict[str, Any]]:
        """
        Get cached tables for a database
        
        Args:
            db_id: Database connection ID
            schema: Schema name
            
        Returns:
            List of table dictionaries
        """
        with get_session() as session:
            tables = session.query(TableCache).filter(
                and_(
                    TableCache.database_id == db_id,
                    TableCache.schema_name == schema
                )
            ).all()
            
            # Convert to dicts to avoid detached instance issues
            result = []
            for table in tables:
                result.append({
                    'id': table.id,
                    'table_name': table.table_name,
                    'schema_name': table.schema_name,
                    'row_count': table.row_count,
                    'column_count': table.column_count,
                    'has_primary_key': table.has_primary_key
                })
            return result
    
    @staticmethod
    def get_table_columns(db_id: str, table_name: str, schema: str = 'public') -> List[ColumnCache]:
        """
        Get columns for a specific table
        
        Args:
            db_id: Database connection ID
            table_name: Table name
            schema: Schema name
            
        Returns:
            List of ColumnCache objects
        """
        with get_session() as session:
            columns = session.query(ColumnCache).join(TableCache).filter(
                and_(
                    TableCache.database_id == db_id,
                    TableCache.table_name == table_name,
                    TableCache.schema_name == schema
                )
            ).all()
            return columns
    
    @staticmethod
    def get_relationships(db_id: str) -> List[RelationshipCache]:
        """
        Get cached relationships for a database
        
        Args:
            db_id: Database connection ID
            
        Returns:
            List of RelationshipCache objects
        """
        with get_session() as session:
            relationships = session.query(RelationshipCache).filter_by(
                database_id=db_id
            ).all()
            return relationships
    
    @staticmethod
    def save_query_history(
        db_id: str,
        sql: str,
        natural_query: Optional[str] = None,
        execution_time: Optional[float] = None,
        row_count: Optional[int] = None,
        status: str = 'success',
        error: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> QueryHistory:
        """
        Save query execution history
        
        Args:
            db_id: Database connection ID
            sql: SQL query
            natural_query: Natural language query
            execution_time: Execution time in seconds
            row_count: Number of rows returned
            status: Query status
            error: Error message if failed
            confidence: AI confidence score
            
        Returns:
            QueryHistory object
        """
        with get_session() as session:
            # Determine query type
            sql_upper = sql.strip().upper()
            if sql_upper.startswith('SELECT'):
                query_type = 'SELECT'
            elif sql_upper.startswith('INSERT'):
                query_type = 'INSERT'
            elif sql_upper.startswith('UPDATE'):
                query_type = 'UPDATE'
            elif sql_upper.startswith('DELETE'):
                query_type = 'DELETE'
            else:
                query_type = 'OTHER'
            
            query = QueryHistory(
                database_id=db_id,
                natural_language_query=natural_query,
                generated_sql=sql,
                query_type=query_type,
                execution_time=execution_time,
                row_count=row_count,
                status=status,
                error_message=error,
                confidence_score=confidence
            )
            session.add(query)
            session.commit()
            session.refresh(query)
            
            logger.info(f"Saved query history: {query_type} query for {db_id}")
            
            # Return a dict to avoid detached instance issues
            result = {
                'id': query.id,
                'database_id': query.database_id,
                'query_type': query.query_type,
                'status': query.status,
                'execution_time': query.execution_time,
                'row_count': query.row_count
            }
            return result
    
    @staticmethod
    def get_query_history(
        db_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[QueryHistory]:
        """
        Get query history
        
        Args:
            db_id: Database connection ID (optional)
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of QueryHistory objects
        """
        with get_session() as session:
            query = session.query(QueryHistory)
            
            if db_id:
                query = query.filter_by(database_id=db_id)
            
            queries = query.order_by(QueryHistory.executed_at.desc()).limit(limit).offset(offset).all()
            return queries
    
    @staticmethod
    def save_ai_insight(
        db_id: str,
        target_type: str,
        target_name: str,
        insight_type: str,
        title: str,
        description: str,
        severity: str = 'info',
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AIInsight:
        """
        Save an AI-generated insight
        
        Args:
            db_id: Database connection ID
            target_type: Type of target (database, table, column, relationship)
            target_name: Name of target
            insight_type: Type of insight
            title: Insight title
            description: Insight description
            severity: Severity level
            confidence: Confidence score
            metadata: Additional metadata
            
        Returns:
            AIInsight object
        """
        with get_session() as session:
            insight = AIInsight(
                database_id=db_id,
                target_type=target_type,
                target_name=target_name,
                insight_type=insight_type,
                title=title,
                description=description,
                severity=severity,
                confidence=confidence,
                extra_data=metadata
            )
            session.add(insight)
            session.commit()
            session.refresh(insight)
            
            logger.info(f"Saved AI insight: {insight_type} for {target_name}")
            
            # Return a dict to avoid detached instance issues
            result = {
                'id': insight.id,
                'title': insight.title,
                'description': insight.description,
                'severity': insight.severity,
                'target_name': insight.target_name
            }
            return result
    
    @staticmethod
    def get_ai_insights(
        db_id: str,
        target_type: Optional[str] = None,
        insight_type: Optional[str] = None
    ) -> List[AIInsight]:
        """
        Get AI insights
        
        Args:
            db_id: Database connection ID
            target_type: Filter by target type
            insight_type: Filter by insight type
            
        Returns:
            List of AIInsight objects
        """
        with get_session() as session:
            query = session.query(AIInsight).filter_by(database_id=db_id)
            
            if target_type:
                query = query.filter_by(target_type=target_type)
            if insight_type:
                query = query.filter_by(insight_type=insight_type)
            
            insights = query.order_by(AIInsight.created_at.desc()).all()
            return insights
    
    @staticmethod
    def create_schema_snapshot(db_id: str, schema_data: Dict[str, Any]) -> SchemaSnapshot:
        """
        Create a schema snapshot for change tracking
        
        Args:
            db_id: Database connection ID
            schema_data: Complete schema structure
            
        Returns:
            SchemaSnapshot object
        """
        with get_session() as session:
            # Create hash of schema
            schema_json = json.dumps(schema_data, sort_keys=True)
            schema_hash = hashlib.sha256(schema_json.encode()).hexdigest()
            
            # Check if schema has changed
            last_snapshot = session.query(SchemaSnapshot).filter_by(
                database_id=db_id
            ).order_by(SchemaSnapshot.created_at.desc()).first()
            
            if last_snapshot and last_snapshot.snapshot_hash == schema_hash:
                logger.info(f"Schema unchanged for {db_id}")
                return last_snapshot
            
            # Calculate changes if there's a previous snapshot
            changes = {
                'tables_added': 0,
                'tables_removed': 0,
                'tables_modified': 0,
                'columns_added': 0,
                'columns_removed': 0,
                'columns_modified': 0
            }
            
            if last_snapshot:
                # Compare schemas
                old_schema = last_snapshot.schema_json
                # TODO: Implement detailed change tracking
            
            snapshot = SchemaSnapshot(
                database_id=db_id,
                snapshot_hash=schema_hash,
                schema_json=schema_data,
                **changes
            )
            session.add(snapshot)
            session.commit()
            
            logger.info(f"Created schema snapshot for {db_id}")
            return snapshot
    
    @staticmethod
    def cleanup_old_data(days: int = 30):
        """
        Clean up old cache data
        
        Args:
            days: Number of days to keep data
        """
        with get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Clean old query history
            deleted_queries = session.query(QueryHistory).filter(
                QueryHistory.executed_at < cutoff_date
            ).delete()
            
            # Clean expired insights
            deleted_insights = session.query(AIInsight).filter(
                or_(
                    AIInsight.expires_at < datetime.utcnow(),
                    AIInsight.created_at < cutoff_date
                )
            ).delete()
            
            # Clean old snapshots (keep last 10 per database)
            # TODO: Implement snapshot cleanup
            
            session.commit()
            logger.info(f"Cleaned up {deleted_queries} old queries and {deleted_insights} expired insights")
    
    def set_cache(self, key: str, data: Dict[str, Any], cache_type: str, ttl: int = 86400) -> None:
        """
        Store data in cache using AI insights as storage mechanism
        
        Args:
            key: Cache key
            data: Data to store
            cache_type: Type of cache entry
            ttl: Time to live in seconds
        """
        try:
            # Use AI insights as a generic cache storage
            with get_session() as session:
                # Remove existing entry with same key
                session.query(AIInsight).filter(
                    and_(
                        AIInsight.target_name == key,
                        AIInsight.insight_type == f'cache_{cache_type}'
                    )
                ).delete()
                
                # Calculate expiry
                expires_at = datetime.utcnow() + timedelta(seconds=ttl)
                
                # Create new cache entry
                insight = AIInsight(
                    database_id='system',
                    target_type='cache',
                    target_name=key,
                    insight_type=f'cache_{cache_type}',
                    title=f'Cache: {cache_type}',
                    description=f'Cached data for {key}',
                    severity='info',
                    confidence=1.0,
                    extra_data=data,
                    expires_at=expires_at
                )
                session.add(insight)
                session.commit()
                
        except Exception as e:
            logger.error(f"Error setting cache for {key}: {e}")
    
    def get_cache(self, key: str, cache_type: str) -> Optional[Dict[str, Any]]:
        """
        Get data from cache
        
        Args:
            key: Cache key
            cache_type: Type of cache entry
            
        Returns:
            Cached data or None if not found/expired
        """
        try:
            with get_session() as session:
                insight = session.query(AIInsight).filter(
                    and_(
                        AIInsight.target_name == key,
                        AIInsight.insight_type == f'cache_{cache_type}',
                        or_(
                            AIInsight.expires_at.is_(None),
                            AIInsight.expires_at > datetime.utcnow()
                        )
                    )
                ).first()
                
                if insight and insight.extra_data:
                    return insight.extra_data
                    
                return None
                
        except Exception as e:
            logger.error(f"Error getting cache for {key}: {e}")
            return None