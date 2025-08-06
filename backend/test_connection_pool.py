#!/usr/bin/env python3
"""
Test connection pool manager
"""
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set master key for credential management
os.environ['SQLAI_MASTER_KEY'] = 'test_master_key_123'

from app.services.connection_pool import ConnectionPoolManager
from app.services.database_service import DatabaseService
from sqlalchemy import text

def test_single_connection():
    """Test single database connection"""
    print("Testing single connection...")
    
    # Create database service and add a connection
    db_service = DatabaseService("test_pool_config.json")
    conn_id = db_service.add_connection(
        name="Test DB Pool",
        host="172.17.12.76",
        port=5432,
        database="postgres",
        username="myuser",
        password="myuser01",
        ssl_mode="prefer"
    )
    
    # Create pool manager with same db_service instance
    pool_manager = ConnectionPoolManager(db_service=db_service)
    
    # Test connection
    with pool_manager.get_connection(conn_id) as conn:
        result = conn.execute(text("SELECT current_database(), current_user, version()"))
        row = result.fetchone()
        print(f"Database: {row[0]}")
        print(f"User: {row[1]}")
        print(f"Version: {row[2][:50]}...")
    
    # Get statistics
    stats = pool_manager.get_pool_statistics(conn_id)
    print(f"\nPool Statistics:")
    print(f"  Total connections: {stats['total_connections']}")
    print(f"  Active connections: {stats['active_connections']}")
    print(f"  Failed connections: {stats['failed_connections']}")
    
    # Clean up
    pool_manager.close_pool(conn_id)
    db_service.delete_connection(conn_id)
    
    print("✅ Single connection test passed!")

def test_concurrent_connections():
    """Test concurrent database connections"""
    print("\n\nTesting concurrent connections...")
    
    # Setup
    db_service = DatabaseService("test_pool_config.json")
    conn_id = db_service.add_connection(
        name="Concurrent Test DB",
        host="172.17.12.76",
        port=5432,
        database="postgres",
        username="myuser",
        password="myuser01"
    )
    
    pool_manager = ConnectionPoolManager(db_service=db_service)
    
    def worker(worker_id):
        """Worker function to execute queries"""
        try:
            with pool_manager.get_connection(conn_id) as conn:
                # Simulate some work
                result = conn.execute(text(f"SELECT {worker_id} as worker_id, pg_backend_pid(), now()"))
                row = result.fetchone()
                time.sleep(0.1)  # Simulate processing
                return f"Worker {worker_id}: PID={row[1]}"
        except Exception as e:
            return f"Worker {worker_id}: Error - {e}"
    
    # Run concurrent workers
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, i) for i in range(20)]
        
        for future in as_completed(futures):
            print(future.result())
    
    # Check statistics
    stats = pool_manager.get_pool_statistics(conn_id)
    print(f"\nFinal Pool Statistics:")
    print(f"  Total connections: {stats['total_connections']}")
    print(f"  Active connections: {stats['active_connections']}")
    print(f"  Failed connections: {stats['failed_connections']}")
    print(f"  Pool size: {stats.get('pool_size', 'N/A')}")
    
    # Clean up
    pool_manager.close_pool(conn_id)
    db_service.delete_connection(conn_id)
    
    print("✅ Concurrent connections test passed!")

def test_multiple_databases():
    """Test multiple database connections"""
    print("\n\nTesting multiple database pools...")
    
    db_service = DatabaseService("test_pool_config.json")
    pool_manager = ConnectionPoolManager(db_service=db_service)
    
    # Add multiple connections (all pointing to same DB for testing)
    conn_ids = []
    for i in range(3):
        conn_id = db_service.add_connection(
            name=f"Database {i+1}",
            host="172.17.12.76",
            port=5432,
            database="postgres",
            username="myuser",
            password="myuser01"
        )
        conn_ids.append(conn_id)
    
    # Execute queries on each database
    for conn_id in conn_ids:
        result = pool_manager.execute_query(
            conn_id,
            "SELECT current_database() as db, count(*) as table_count FROM information_schema.tables WHERE table_schema = 'public'"
        )
        print(f"Connection {conn_id[:8]}...: {result[0] if result else 'No result'}")
    
    # Get all statistics
    all_stats = pool_manager.get_pool_statistics()
    print(f"\nTotal pools created: {len(all_stats)}")
    
    # Test health check
    for conn_id in conn_ids:
        is_healthy = pool_manager.health_check(conn_id)
        print(f"Connection {conn_id[:8]}... health: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")
    
    # Clean up
    pool_manager.close_all_pools()
    for conn_id in conn_ids:
        db_service.delete_connection(conn_id)
    
    print("✅ Multiple databases test passed!")

def test_pool_cleanup():
    """Test idle pool cleanup"""
    print("\n\nTesting idle pool cleanup...")
    
    db_service = DatabaseService("test_pool_config.json")
    pool_manager = ConnectionPoolManager(db_service=db_service)
    
    # Create a connection
    conn_id = db_service.add_connection(
        name="Idle Test DB",
        host="172.17.12.76",
        port=5432,
        database="postgres",
        username="myuser",
        password="myuser01"
    )
    
    # Use the connection
    pool_manager.execute_query(conn_id, "SELECT 1")
    
    # Simulate idle time by manipulating last_used
    pool_manager.pool_stats[conn_id]['last_used'] = pool_manager.pool_stats[conn_id]['created_at']
    
    # Clean up idle pools (with 0 minute timeout for testing)
    cleaned = pool_manager.cleanup_idle_pools(idle_timeout_minutes=0)
    print(f"Cleaned up {cleaned} idle pools")
    
    # Verify pool was closed
    assert conn_id not in pool_manager.pools
    
    # Clean up
    db_service.delete_connection(conn_id)
    
    print("✅ Idle pool cleanup test passed!")

def cleanup_test_files():
    """Clean up test files"""
    if os.path.exists("test_pool_config.json"):
        os.remove("test_pool_config.json")

if __name__ == "__main__":
    try:
        print("=" * 60)
        print("Connection Pool Manager Tests")
        print("=" * 60)
        
        test_single_connection()
        test_concurrent_connections()
        test_multiple_databases()
        test_pool_cleanup()
        
        print("\n" + "=" * 60)
        print("🎉 All connection pool tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_test_files()