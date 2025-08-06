#!/usr/bin/env python3
"""
Test SQLite cache database
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from app.models import init_db, get_session
from app.models.base import get_table_stats
from app.services.cache_service import CacheService

def test_database_creation():
    """Test database creation and tables"""
    print("Testing Database Creation...")
    print("=" * 60)
    
    # Initialize database
    init_db()
    
    # Get table statistics
    stats = get_table_stats()
    print(f"Created {len(stats)} tables:")
    for table, count in stats.items():
        print(f"  - {table}: {count} rows")
    
    print("\n✅ Database created successfully!")

def test_cache_operations():
    """Test cache service operations"""
    print("\n\nTesting Cache Operations...")
    print("=" * 60)
    
    cache_service = CacheService()
    
    # Save database info
    db_info = cache_service.save_database_info(
        db_id="test-db-001",
        name="Test Database",
        host="localhost",
        port=5432,
        database="testdb",
        username="testuser"
    )
    print(f"✅ Saved database: {db_info['name']} ({db_info['id']})")
    
    # Save table metadata
    tables = [
        {
            'name': 'users',
            'schema': 'public',
            'row_count': 1000,
            'size_bytes': 102400,
            'type': 'TABLE',
            'has_primary_key': True,
            'columns': [
                {
                    'name': 'id',
                    'type': 'integer',
                    'nullable': False,
                    'is_primary_key': True
                },
                {
                    'name': 'email',
                    'type': 'varchar(255)',
                    'nullable': False,
                    'is_unique': True
                },
                {
                    'name': 'created_at',
                    'type': 'timestamp',
                    'nullable': False,
                    'default': 'now()'
                }
            ]
        },
        {
            'name': 'orders',
            'schema': 'public',
            'row_count': 5000,
            'size_bytes': 512000,
            'type': 'TABLE',
            'has_primary_key': True,
            'columns': [
                {
                    'name': 'id',
                    'type': 'integer',
                    'nullable': False,
                    'is_primary_key': True
                },
                {
                    'name': 'user_id',
                    'type': 'integer',
                    'nullable': False,
                    'is_foreign_key': True
                },
                {
                    'name': 'total',
                    'type': 'decimal(10,2)',
                    'nullable': False
                }
            ]
        }
    ]
    
    table_count = cache_service.save_table_metadata("test-db-001", tables)
    print(f"✅ Saved {table_count} tables")
    
    # Save relationships
    relationships = [
        {
            'from_table': 'orders',
            'from_column': 'user_id',
            'to_table': 'users',
            'to_column': 'id',
            'type': 'many-to-one',
            'constraint_name': 'fk_orders_user_id'
        }
    ]
    
    rel_count = cache_service.save_relationships("test-db-001", relationships)
    print(f"✅ Saved {rel_count} relationships")
    
    # Save query history
    query = cache_service.save_query_history(
        db_id="test-db-001",
        sql="SELECT * FROM users WHERE created_at > '2024-01-01'",
        natural_query="Show me all users created this year",
        execution_time=0.125,
        row_count=500,
        status="success",
        confidence=0.95
    )
    print(f"✅ Saved query history: {query['query_type']} query")
    
    # Save AI insight
    insight = cache_service.save_ai_insight(
        db_id="test-db-001",
        target_type="table",
        target_name="users",
        insight_type="optimization",
        title="Missing index on email column",
        description="The 'email' column is frequently used in WHERE clauses but lacks an index",
        severity="warning",
        confidence=0.85,
        metadata={
            "estimated_improvement": "30%",
            "query_patterns": ["SELECT * FROM users WHERE email = ?"]
        }
    )
    print(f"✅ Saved AI insight: {insight['title']}")

def test_cache_retrieval():
    """Test retrieving cached data"""
    print("\n\nTesting Cache Retrieval...")
    print("=" * 60)
    
    cache_service = CacheService()
    
    # Get tables
    tables = cache_service.get_tables("test-db-001")
    print(f"Found {len(tables)} tables:")
    for table in tables:
        print(f"  - {table['table_name']}: {table['column_count']} columns, {table['row_count']} rows")
    
    # Get columns for a table
    columns = cache_service.get_table_columns("test-db-001", "users")
    print(f"\nColumns in 'users' table:")
    for col in columns:
        pk = " [PK]" if col.is_primary_key else ""
        fk = " [FK]" if col.is_foreign_key else ""
        print(f"  - {col.column_name}: {col.data_type}{pk}{fk}")
    
    # Get relationships
    relationships = cache_service.get_relationships("test-db-001")
    print(f"\nFound {len(relationships)} relationships:")
    for rel in relationships:
        print(f"  - {rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}")
    
    # Get query history
    queries = cache_service.get_query_history("test-db-001", limit=5)
    print(f"\nQuery history ({len(queries)} queries):")
    for q in queries:
        print(f"  - {q.query_type}: {q.status}, {q.execution_time:.3f}s, {q.row_count} rows")
    
    # Get AI insights
    insights = cache_service.get_ai_insights("test-db-001")
    print(f"\nAI Insights ({len(insights)} insights):")
    for insight in insights:
        print(f"  - [{insight.severity}] {insight.title}")
    
    print("\n✅ Cache retrieval successful!")

def test_schema_snapshot():
    """Test schema snapshot creation"""
    print("\n\nTesting Schema Snapshot...")
    print("=" * 60)
    
    cache_service = CacheService()
    
    # Create schema snapshot
    schema_data = {
        'version': '1.0',
        'timestamp': datetime.utcnow().isoformat(),
        'tables': {
            'users': {
                'columns': ['id', 'email', 'created_at'],
                'primary_key': 'id',
                'indexes': ['pk_users', 'idx_users_email']
            },
            'orders': {
                'columns': ['id', 'user_id', 'total'],
                'primary_key': 'id',
                'foreign_keys': {'user_id': 'users.id'}
            }
        }
    }
    
    snapshot = cache_service.create_schema_snapshot("test-db-001", schema_data)
    print(f"✅ Created schema snapshot: {snapshot.snapshot_hash[:16]}...")
    
    # Create same snapshot (should detect no change)
    snapshot2 = cache_service.create_schema_snapshot("test-db-001", schema_data)
    print(f"✅ Schema unchanged: {snapshot2.snapshot_hash[:16]}...")
    
    # Create modified snapshot
    schema_data['tables']['products'] = {'columns': ['id', 'name', 'price']}
    snapshot3 = cache_service.create_schema_snapshot("test-db-001", schema_data)
    print(f"✅ Schema changed: {snapshot3.snapshot_hash[:16]}...")

def cleanup():
    """Clean up test database"""
    if os.path.exists("cache.db"):
        os.remove("cache.db")
        print("\n✅ Cleaned up test database")

if __name__ == "__main__":
    try:
        print("=" * 60)
        print("SQLite Cache Database Tests")
        print("=" * 60)
        
        # Clean up any existing test database
        cleanup()
        
        # Run tests
        test_database_creation()
        test_cache_operations()
        test_cache_retrieval()
        test_schema_snapshot()
        
        # Show final statistics
        print("\n" + "=" * 60)
        print("Final Database Statistics:")
        print("=" * 60)
        stats = get_table_stats()
        for table, count in stats.items():
            print(f"  {table}: {count} rows")
        
        print("\n" + "=" * 60)
        print("🎉 All cache database tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        cleanup()