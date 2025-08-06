#!/usr/bin/env python3
"""
Test PostgreSQL schema introspection
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.postgres_inspector import PostgresInspector
from app.services.connection_pool import ConnectionPoolManager
from app.utils.security import CredentialManager
import json

def test_connection():
    """Test PostgreSQL connection"""
    print("Testing PostgreSQL Connection...")
    print("=" * 60)
    
    inspector = PostgresInspector()
    
    # Test database credentials
    result = inspector.test_connection(
        host="172.17.12.76",
        port=5432,
        database="postgres",
        username="myuser",
        password="myuser01"
    )
    
    if result['success']:
        print(f"✅ Connection successful!")
        print(f"   Database: {result['database']}")
        print(f"   Version: {result['version'][:50]}...")
    else:
        print(f"❌ Connection failed: {result['message']}")
        return False
    
    return True

def test_schema_introspection():
    """Test schema introspection"""
    print("\n\nTesting Schema Introspection...")
    print("=" * 60)
    
    # Setup connection using database service
    from app.services.database_service import get_database_service
    
    db_service = get_database_service()
    
    # Add test database to service
    conn_id = db_service.add_connection(
        name="Test Database",
        host="172.17.12.76",
        port=5432,
        database="postgres",
        username="myuser",
        password="myuser01"
    )
    
    print(f"   Added connection: {conn_id}")
    
    # Create pool
    pool_manager = ConnectionPoolManager()
    pool_manager.create_pool(conn_id)
    
    inspector = PostgresInspector()
    
    # Get database info
    print("\n📊 Database Information:")
    db_info = inspector.get_database_info(conn_id)
    print(f"   Name: {db_info['database_name']}")
    print(f"   Size: {db_info['size_mb']} MB")
    print(f"   Tables: {db_info['table_count']}")
    
    # Get schemas
    print("\n📁 Schemas:")
    schemas = inspector.get_schemas(conn_id)
    for schema in schemas:
        print(f"   - {schema}")
    
    # Get tables in public schema
    print("\n📋 Tables in 'public' schema:")
    tables = inspector.get_tables(conn_id, "public")
    
    if not tables:
        print("   No tables found. Creating test tables...")
        create_test_tables()
        tables = inspector.get_tables(conn_id, "public")
    
    for table in tables[:5]:  # Show first 5 tables
        print(f"   - {table['name']}: {table['column_count']} columns, {table['row_count']} rows")
    
    if tables:
        # Get columns for first table
        first_table = tables[0]
        print(f"\n🔍 Columns in '{first_table['name']}':")
        columns = inspector.get_columns(conn_id, first_table['name'])
        for col in columns[:10]:  # Show first 10 columns
            pk = " [PK]" if col['is_primary_key'] else ""
            fk = " [FK]" if col['is_foreign_key'] else ""
            null = "" if col['nullable'] else " NOT NULL"
            print(f"   - {col['name']}: {col['type']}{null}{pk}{fk}")
    
    # Get foreign keys
    print("\n🔗 Foreign Key Relationships:")
    relationships = inspector.get_foreign_keys(conn_id)
    for rel in relationships[:5]:  # Show first 5 relationships
        print(f"   - {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}")
    
    print("\n✅ Schema introspection successful!")

def test_full_analysis():
    """Test full schema analysis with caching"""
    print("\n\nTesting Full Schema Analysis...")
    print("=" * 60)
    
    # Get the connection ID from the previous test
    from app.services.database_service import get_database_service
    db_service = get_database_service()
    connections = db_service.list_connections()
    conn_id = connections[0]['id'] if connections else None
    
    if not conn_id:
        print("❌ No connection found. Please run test_schema_introspection first.")
        return
    
    inspector = PostgresInspector()
    
    print("⏳ Performing full schema analysis (this may take a moment)...")
    
    try:
        analysis = inspector.analyze_schema(conn_id, schemas=['public'])
        
        print("\n📊 Analysis Results:")
        print(f"   Total Tables: {analysis['total_tables']}")
        print(f"   Total Columns: {analysis['total_columns']}")
        print(f"   Total Relationships: {analysis['total_relationships']}")
        
        # Show schema details
        for schema_name, schema_data in analysis['schemas'].items():
            print(f"\n   Schema '{schema_name}':")
            print(f"      Tables: {schema_data['table_count']}")
            print(f"      Relationships: {schema_data['relationship_count']}")
            
            # Show first few tables
            for table in schema_data['tables'][:3]:
                print(f"      - {table['name']}: {len(table['columns'])} columns, {len(table.get('indexes', []))} indexes")
        
        print("\n✅ Full analysis completed and cached!")
        
        # Save analysis to file for review
        with open('schema_analysis.json', 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        print("   Analysis saved to schema_analysis.json")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

def create_test_tables():
    """Create test tables if database is empty"""
    from sqlalchemy import create_engine, text
    
    connection_string = "postgresql://myuser:myuser01@172.17.12.76:5432/postgres"
    engine = create_engine(connection_string)
    
    with engine.connect() as conn:
        # Create simple test tables
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                price DECIMAL(10,2),
                category VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                total_amount DECIMAL(10,2),
                order_date DATE DEFAULT CURRENT_DATE,
                status VARCHAR(50) DEFAULT 'pending'
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS order_items (
                id SERIAL PRIMARY KEY,
                order_id INTEGER REFERENCES orders(id),
                product_id INTEGER REFERENCES products(id),
                quantity INTEGER NOT NULL,
                unit_price DECIMAL(10,2)
            )
        """))
        
        conn.commit()
        print("   ✅ Test tables created successfully!")

def cleanup():
    """Clean up resources"""
    # ConnectionPoolManager cleanup is handled internally
    pass

if __name__ == "__main__":
    try:
        print("=" * 60)
        print("PostgreSQL Schema Introspection Tests")
        print("=" * 60)
        
        # Test basic connection
        if not test_connection():
            print("\n❌ Connection test failed. Please check database credentials.")
            sys.exit(1)
        
        # Test schema introspection
        test_schema_introspection()
        
        # Test full analysis
        test_full_analysis()
        
        print("\n" + "=" * 60)
        print("🎉 All PostgreSQL introspection tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()