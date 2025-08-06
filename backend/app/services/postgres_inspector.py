"""
PostgreSQL Schema Introspection Service
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text, inspect, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool
import psycopg2
from psycopg2.extras import RealDictCursor

from app.services.connection_pool import ConnectionPoolManager
from app.services.cache_service import CacheService
from app.utils.security import CredentialManager

logger = logging.getLogger(__name__)

class PostgresInspector:
    """PostgreSQL database schema introspection service"""
    
    def __init__(self):
        self.pool_manager = ConnectionPoolManager()
        self.cache_service = CacheService()
        self.credential_manager = CredentialManager()
    
    def get_database_info(self, db_id: str) -> Dict[str, Any]:
        """
        Get basic database information
        
        Args:
            db_id: Database connection ID
            
        Returns:
            Database information dictionary
        """
        engine = self.pool_manager.get_engine(db_id)
        
        with engine.connect() as conn:
            # Get PostgreSQL version
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            
            # Get database size
            result = conn.execute(text(
                "SELECT pg_database_size(current_database()) as size"
            ))
            db_size = result.scalar()
            
            # Get current database name
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            
            # Get table count
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                AND table_type = 'BASE TABLE'
            """))
            table_count = result.scalar()
            
            return {
                'database_name': db_name,
                'version': version,
                'size_bytes': db_size,
                'size_mb': round(db_size / (1024 * 1024), 2),
                'table_count': table_count
            }
    
    def get_schemas(self, db_id: str) -> List[str]:
        """
        Get all schemas in the database
        
        Args:
            db_id: Database connection ID
            
        Returns:
            List of schema names
        """
        engine = self.pool_manager.get_engine(db_id)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                ORDER BY schema_name
            """))
            
            schemas = [row[0] for row in result]
            logger.info(f"Found {len(schemas)} schemas in database {db_id}")
            return schemas
    
    def get_tables(self, db_id: str, schema: str = 'public') -> List[Dict[str, Any]]:
        """
        Get all tables in a schema with metadata
        
        Args:
            db_id: Database connection ID
            schema: Schema name
            
        Returns:
            List of table metadata dictionaries
        """
        engine = self.pool_manager.get_engine(db_id)
        
        with engine.connect() as conn:
            # Get table information
            query = text("""
                SELECT 
                    t.table_name,
                    t.table_schema,
                    t.table_type,
                    obj_description(pgc.oid, 'pg_class') as table_comment,
                    pg_relation_size(pgc.oid) as size_bytes,
                    pgc.reltuples::bigint as estimated_row_count,
                    (
                        SELECT COUNT(*) 
                        FROM information_schema.columns c 
                        WHERE c.table_schema = t.table_schema 
                        AND c.table_name = t.table_name
                    ) as column_count,
                    (
                        SELECT COUNT(*) > 0
                        FROM information_schema.table_constraints tc
                        WHERE tc.table_schema = t.table_schema
                        AND tc.table_name = t.table_name
                        AND tc.constraint_type = 'PRIMARY KEY'
                    ) as has_primary_key
                FROM information_schema.tables t
                JOIN pg_class pgc ON pgc.relname = t.table_name
                JOIN pg_namespace pgn ON pgn.oid = pgc.relnamespace 
                    AND pgn.nspname = t.table_schema
                WHERE t.table_schema = :schema
                AND t.table_type IN ('BASE TABLE', 'VIEW')
                ORDER BY t.table_name
            """)
            
            result = conn.execute(query, {'schema': schema})
            tables = []
            
            for row in result:
                table_data = {
                    'name': row[0],
                    'schema': row[1],
                    'type': row[2],
                    'description': row[3],
                    'size_bytes': row[4] or 0,
                    'row_count': row[5] or 0,
                    'column_count': row[6],
                    'has_primary_key': row[7]
                }
                tables.append(table_data)
            
            logger.info(f"Found {len(tables)} tables in schema {schema}")
            return tables
    
    def get_columns(self, db_id: str, table_name: str, schema: str = 'public') -> List[Dict[str, Any]]:
        """
        Get column information for a table
        
        Args:
            db_id: Database connection ID
            table_name: Table name
            schema: Schema name
            
        Returns:
            List of column metadata dictionaries
        """
        engine = self.pool_manager.get_engine(db_id)
        
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    c.column_name,
                    c.data_type,
                    c.udt_name,
                    c.character_maximum_length,
                    c.numeric_precision,
                    c.numeric_scale,
                    c.is_nullable,
                    c.column_default,
                    c.ordinal_position,
                    col_description(pgc.oid, c.ordinal_position) as column_comment,
                    (
                        SELECT COUNT(*) > 0
                        FROM information_schema.key_column_usage kcu
                        JOIN information_schema.table_constraints tc
                            ON tc.constraint_name = kcu.constraint_name
                            AND tc.table_schema = kcu.table_schema
                        WHERE kcu.table_schema = c.table_schema
                        AND kcu.table_name = c.table_name
                        AND kcu.column_name = c.column_name
                        AND tc.constraint_type = 'PRIMARY KEY'
                    ) as is_primary_key,
                    (
                        SELECT COUNT(*) > 0
                        FROM information_schema.key_column_usage kcu
                        JOIN information_schema.table_constraints tc
                            ON tc.constraint_name = kcu.constraint_name
                            AND tc.table_schema = kcu.table_schema
                        WHERE kcu.table_schema = c.table_schema
                        AND kcu.table_name = c.table_name
                        AND kcu.column_name = c.column_name
                        AND tc.constraint_type = 'FOREIGN KEY'
                    ) as is_foreign_key,
                    (
                        SELECT COUNT(*) > 0
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.constraint_column_usage ccu
                            ON tc.constraint_name = ccu.constraint_name
                            AND tc.table_schema = ccu.table_schema
                        WHERE ccu.table_schema = c.table_schema
                        AND ccu.table_name = c.table_name
                        AND ccu.column_name = c.column_name
                        AND tc.constraint_type = 'UNIQUE'
                    ) as is_unique
                FROM information_schema.columns c
                JOIN pg_class pgc ON pgc.relname = c.table_name
                JOIN pg_namespace pgn ON pgn.oid = pgc.relnamespace 
                    AND pgn.nspname = c.table_schema
                WHERE c.table_schema = :schema
                AND c.table_name = :table_name
                ORDER BY c.ordinal_position
            """)
            
            result = conn.execute(query, {'schema': schema, 'table_name': table_name})
            columns = []
            
            for row in result:
                column_data = {
                    'name': row[0],
                    'type': row[1],
                    'udt_name': row[2],
                    'max_length': row[3],
                    'numeric_precision': row[4],
                    'numeric_scale': row[5],
                    'nullable': row[6] == 'YES',
                    'default': row[7],
                    'ordinal_position': row[8],
                    'description': row[9],
                    'is_primary_key': row[10],
                    'is_foreign_key': row[11],
                    'is_unique': row[12]
                }
                columns.append(column_data)
            
            logger.info(f"Found {len(columns)} columns in table {schema}.{table_name}")
            return columns
    
    def get_foreign_keys(self, db_id: str, schema: str = 'public') -> List[Dict[str, Any]]:
        """
        Get all foreign key relationships in a schema
        
        Args:
            db_id: Database connection ID
            schema: Schema name
            
        Returns:
            List of foreign key relationship dictionaries
        """
        engine = self.pool_manager.get_engine(db_id)
        
        with engine.connect() as conn:
            query = text("""
                SELECT
                    tc.constraint_name,
                    tc.table_schema as from_schema,
                    tc.table_name as from_table,
                    kcu.column_name as from_column,
                    ccu.table_schema as to_schema,
                    ccu.table_name as to_table,
                    ccu.column_name as to_column,
                    rc.update_rule as on_update,
                    rc.delete_rule as on_delete
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                JOIN information_schema.referential_constraints rc
                    ON rc.constraint_name = tc.constraint_name
                    AND rc.constraint_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = :schema
                ORDER BY tc.table_name, kcu.ordinal_position
            """)
            
            result = conn.execute(query, {'schema': schema})
            relationships = []
            
            for row in result:
                rel_data = {
                    'constraint_name': row[0],
                    'from_schema': row[1],
                    'from_table': row[2],
                    'from_column': row[3],
                    'to_schema': row[4],
                    'to_table': row[5],
                    'to_column': row[6],
                    'on_update': row[7],
                    'on_delete': row[8],
                    'type': 'many-to-one'  # Default, will be refined later
                }
                relationships.append(rel_data)
            
            logger.info(f"Found {len(relationships)} foreign key relationships in schema {schema}")
            return relationships
    
    def get_indexes(self, db_id: str, table_name: str, schema: str = 'public') -> List[Dict[str, Any]]:
        """
        Get indexes for a table
        
        Args:
            db_id: Database connection ID
            table_name: Table name
            schema: Schema name
            
        Returns:
            List of index metadata dictionaries
        """
        engine = self.pool_manager.get_engine(db_id)
        
        with engine.connect() as conn:
            query = text("""
                SELECT
                    i.indexname,
                    i.indexdef,
                    idx.indisprimary as is_primary,
                    idx.indisunique as is_unique,
                    pg_relation_size(idx.indexrelid) as size_bytes
                FROM pg_indexes i
                JOIN pg_class c ON c.relname = i.tablename
                JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = i.schemaname
                JOIN pg_index idx ON idx.indrelid = c.oid
                JOIN pg_class ic ON ic.oid = idx.indexrelid AND ic.relname = i.indexname
                WHERE i.schemaname = :schema
                AND i.tablename = :table_name
                ORDER BY i.indexname
            """)
            
            result = conn.execute(query, {'schema': schema, 'table_name': table_name})
            indexes = []
            
            for row in result:
                index_data = {
                    'name': row[0],
                    'definition': row[1],
                    'is_primary': row[2],
                    'is_unique': row[3],
                    'size_bytes': row[4] or 0
                }
                indexes.append(index_data)
            
            logger.info(f"Found {len(indexes)} indexes for table {schema}.{table_name}")
            return indexes
    
    def analyze_schema(self, db_id: str, schemas: List[str] = None) -> Dict[str, Any]:
        """
        Perform comprehensive schema analysis
        
        Args:
            db_id: Database connection ID
            schemas: List of schemas to analyze (default: all)
            
        Returns:
            Complete schema analysis dictionary
        """
        try:
            # Get database info
            db_info = self.get_database_info(db_id)
            
            # Get schemas if not provided
            if not schemas:
                schemas = self.get_schemas(db_id)
                if 'public' not in schemas:
                    schemas.append('public')
            
            analysis = {
                'database': db_info,
                'schemas': {},
                'total_tables': 0,
                'total_columns': 0,
                'total_relationships': 0
            }
            
            all_tables = []
            all_relationships = []
            
            for schema in schemas:
                logger.info(f"Analyzing schema: {schema}")
                
                # Get tables
                tables = self.get_tables(db_id, schema)
                
                # Get columns for each table
                for table in tables:
                    table['columns'] = self.get_columns(db_id, table['name'], schema)
                    table['indexes'] = self.get_indexes(db_id, table['name'], schema)
                
                # Get relationships
                relationships = self.get_foreign_keys(db_id, schema)
                
                analysis['schemas'][schema] = {
                    'tables': tables,
                    'relationships': relationships,
                    'table_count': len(tables),
                    'relationship_count': len(relationships)
                }
                
                all_tables.extend(tables)
                all_relationships.extend(relationships)
                
                analysis['total_tables'] += len(tables)
                analysis['total_columns'] += sum(len(t['columns']) for t in tables)
                analysis['total_relationships'] += len(relationships)
            
            # Save to cache
            logger.info(f"Saving analysis to cache for database {db_id}")
            
            # Get connection details from database service
            from app.services.database_service import get_database_service
            db_service = get_database_service()
            conn_details = db_service.get_connection(db_id)
            
            self.cache_service.save_database_info(
                db_id=db_id,
                name=db_info['database_name'],
                host=conn_details['host'],
                port=conn_details['port'],
                database=db_info['database_name'],
                username=conn_details['username']
            )
            
            self.cache_service.save_table_metadata(db_id, all_tables)
            self.cache_service.save_relationships(db_id, all_relationships)
            
            logger.info(f"Schema analysis complete: {analysis['total_tables']} tables, "
                       f"{analysis['total_columns']} columns, {analysis['total_relationships']} relationships")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Schema analysis failed for database {db_id}: {e}")
            raise
    
    def test_connection(self, host: str, port: int, database: str, 
                       username: str, password: str) -> Dict[str, Any]:
        """
        Test PostgreSQL connection
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            username: Username
            password: Password
            
        Returns:
            Connection test result
        """
        try:
            # Build connection string
            connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
            
            # Create temporary engine
            engine = create_engine(connection_string, poolclass=NullPool)
            
            with engine.connect() as conn:
                # Test basic query
                result = conn.execute(text("SELECT 1"))
                result.scalar()
                
                # Get version
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                
                # Get database name
                result = conn.execute(text("SELECT current_database()"))
                db_name = result.scalar()
                
                return {
                    'success': True,
                    'message': 'Connection successful',
                    'database': db_name,
                    'version': version
                }
                
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_table_statistics(self, db_id: str, table_name: str, schema: str = 'public') -> Dict[str, Any]:
        """
        Get detailed statistics for a table
        
        Args:
            db_id: Database connection ID
            table_name: Table name
            schema: Schema name
            
        Returns:
            Table statistics dictionary
        """
        engine = self.pool_manager.get_engine(db_id)
        
        with engine.connect() as conn:
            # Get basic statistics
            query = text("""
                SELECT 
                    pg_relation_size(:schema||'.'||:table_name) as table_size,
                    pg_total_relation_size(:schema||'.'||:table_name) as total_size,
                    (SELECT COUNT(*) FROM {}.{}) as exact_row_count,
                    pg_stat_get_live_tuples(c.oid) as live_tuples,
                    pg_stat_get_dead_tuples(c.oid) as dead_tuples,
                    pg_stat_get_last_vacuum_time(c.oid) as last_vacuum,
                    pg_stat_get_last_analyze_time(c.oid) as last_analyze
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = :schema
                AND c.relname = :table_name
            """.format(schema, table_name))
            
            result = conn.execute(query, {'schema': schema, 'table_name': table_name})
            row = result.fetchone()
            
            if row:
                return {
                    'table_size_bytes': row[0],
                    'total_size_bytes': row[1],
                    'exact_row_count': row[2],
                    'live_tuples': row[3],
                    'dead_tuples': row[4],
                    'last_vacuum': row[5],
                    'last_analyze': row[6],
                    'table_size_mb': round(row[0] / (1024 * 1024), 2) if row[0] else 0,
                    'total_size_mb': round(row[1] / (1024 * 1024), 2) if row[1] else 0
                }
            
            return {}
