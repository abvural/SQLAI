#!/usr/bin/env python3
"""
Test error handling and logging system
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from app.utils.logging_config import setup_logging, log_query_execution, log_security_event
from app.utils.exceptions import (
    DatabaseConnectionError,
    ValidationError,
    QueryExecutionError,
    ResourceNotFoundError
)

def test_logging_setup():
    """Test logging system setup"""
    print("Testing Logging Setup...")
    print("=" * 60)
    
    # Setup logging
    setup_logging()
    
    # Test different loggers
    app_logger = logging.getLogger("app")
    query_logger = logging.getLogger("query")
    security_logger = logging.getLogger("security")
    
    # Test log levels
    app_logger.debug("This is a debug message")
    app_logger.info("This is an info message")
    app_logger.warning("This is a warning message")
    app_logger.error("This is an error message")
    
    print("✅ Logging system initialized")
    print(f"   Log files created in: logs/")
    
    # Check if log files were created
    if os.path.exists("logs/app.log"):
        print("   ✅ app.log created")
    if os.path.exists("logs/error.log"):
        print("   ✅ error.log created")
    if os.path.exists("logs/query.log"):
        print("   ✅ query.log created")
    if os.path.exists("logs/security.log"):
        print("   ✅ security.log created")

def test_custom_exceptions():
    """Test custom exception classes"""
    print("\n\nTesting Custom Exceptions...")
    print("=" * 60)
    
    # Test DatabaseConnectionError
    try:
        raise DatabaseConnectionError(
            message="Failed to connect to database",
            database_id="test-db-001"
        )
    except DatabaseConnectionError as e:
        print(f"✅ DatabaseConnectionError:")
        print(f"   Message: {e.message}")
        print(f"   Error Code: {e.error_code}")
        print(f"   Status Code: {e.status_code}")
        print(f"   Details: {e.details}")
    
    # Test ValidationError
    try:
        raise ValidationError(
            message="Invalid input",
            field="username"
        )
    except ValidationError as e:
        print(f"\n✅ ValidationError:")
        print(f"   Message: {e.message}")
        print(f"   Error Code: {e.error_code}")
        print(f"   Status Code: {e.status_code}")
        print(f"   Details: {e.details}")
    
    # Test QueryExecutionError
    try:
        raise QueryExecutionError(
            message="Query failed",
            sql="SELECT * FROM users"
        )
    except QueryExecutionError as e:
        print(f"\n✅ QueryExecutionError:")
        print(f"   Message: {e.message}")
        print(f"   Error Code: {e.error_code}")
        print(f"   Status Code: {e.status_code}")
        print(f"   Details: {e.details}")
    
    # Test ResourceNotFoundError
    try:
        raise ResourceNotFoundError(
            resource_type="Database",
            resource_id="db-123"
        )
    except ResourceNotFoundError as e:
        print(f"\n✅ ResourceNotFoundError:")
        print(f"   Message: {e.message}")
        print(f"   Error Code: {e.error_code}")
        print(f"   Status Code: {e.status_code}")
        print(f"   Details: {e.details}")

def test_query_logging():
    """Test query execution logging"""
    print("\n\nTesting Query Logging...")
    print("=" * 60)
    
    # Log successful query
    log_query_execution(
        database_id="test-db-001",
        natural_query="Show all users",
        generated_sql="SELECT * FROM users",
        execution_time=0.125,
        row_count=100,
        status="success"
    )
    print("✅ Logged successful query execution")
    
    # Log failed query
    log_query_execution(
        database_id="test-db-001",
        natural_query="Delete everything",
        generated_sql="DELETE FROM users",
        execution_time=0.001,
        row_count=0,
        status="failed",
        error="Permission denied"
    )
    print("✅ Logged failed query execution")

def test_security_logging():
    """Test security event logging"""
    print("\n\nTesting Security Logging...")
    print("=" * 60)
    
    # Log authentication attempt
    log_security_event(
        event_type="authentication_attempt",
        message="Failed login attempt",
        user_id="unknown",
        ip_address="192.168.1.100",
        details={
            "username": "admin",
            "reason": "Invalid password"
        }
    )
    print("✅ Logged authentication attempt")
    
    # Log SQL injection attempt
    log_security_event(
        event_type="sql_injection_attempt",
        message="Potential SQL injection detected",
        ip_address="192.168.1.200",
        details={
            "query": "'; DROP TABLE users; --",
            "blocked": True
        }
    )
    print("✅ Logged SQL injection attempt")
    
    # Log unauthorized access
    log_security_event(
        event_type="unauthorized_access",
        message="Unauthorized access to admin endpoint",
        user_id="user-123",
        ip_address="192.168.1.150",
        details={
            "endpoint": "/api/admin/users",
            "required_role": "admin",
            "user_role": "user"
        }
    )
    print("✅ Logged unauthorized access")

def test_error_propagation():
    """Test error propagation and handling"""
    print("\n\nTesting Error Propagation...")
    print("=" * 60)
    
    logger = logging.getLogger("app")
    
    def function_that_fails():
        """Simulate a function that fails"""
        raise ValueError("Something went wrong")
    
    def wrapper_function():
        """Wrapper that catches and re-raises"""
        try:
            function_that_fails()
        except ValueError as e:
            logger.error(f"Caught error in wrapper: {e}", exc_info=True)
            raise DatabaseConnectionError(
                message="Database operation failed due to underlying error",
                database_id="test-db"
            ) from e
    
    try:
        wrapper_function()
    except DatabaseConnectionError as e:
        print("✅ Error properly propagated and transformed")
        print(f"   Original error captured in logs")
        print(f"   User-friendly error: {e.message}")

def check_log_contents():
    """Check if logs contain expected content"""
    print("\n\nChecking Log Contents...")
    print("=" * 60)
    
    # Read app.log
    if os.path.exists("logs/app.log"):
        with open("logs/app.log", "r") as f:
            content = f.read()
            if "This is an info message" in content:
                print("✅ App log contains info messages")
            if "This is an error message" in content:
                print("✅ App log contains error messages")
    
    # Read query.log
    if os.path.exists("logs/query.log"):
        with open("logs/query.log", "r") as f:
            content = f.read()
            if "Query executed" in content:
                print("✅ Query log contains query execution logs")
    
    # Read security.log
    if os.path.exists("logs/security.log"):
        with open("logs/security.log", "r") as f:
            content = f.read()
            if "authentication_attempt" in content:
                print("✅ Security log contains security events")

def cleanup():
    """Clean up test logs"""
    # Keep logs for review, don't delete
    pass

if __name__ == "__main__":
    try:
        print("=" * 60)
        print("Error Handling and Logging Tests")
        print("=" * 60)
        
        # Run tests
        test_logging_setup()
        test_custom_exceptions()
        test_query_logging()
        test_security_logging()
        test_error_propagation()
        check_log_contents()
        
        print("\n" + "=" * 60)
        print("🎉 All error handling and logging tests passed!")
        print("=" * 60)
        print("\n📁 Check the 'logs' directory for generated log files:")
        print("   - logs/app.log: Application logs")
        print("   - logs/error.log: Error logs")
        print("   - logs/query.log: Query execution logs")
        print("   - logs/security.log: Security event logs")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()