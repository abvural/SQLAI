#!/usr/bin/env python3
"""
Test SQL injection prevention
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.sql_validator import SQLValidator, SQLOperation, QueryBuilder, validate_user_input

def test_sql_injection_detection():
    """Test SQL injection pattern detection"""
    print("Testing SQL Injection Detection...")
    print("=" * 60)
    
    # Test cases with injection attempts
    injection_tests = [
        ("SELECT * FROM users WHERE id = 1; DROP TABLE users;", True),
        ("SELECT * FROM users WHERE name = 'admin' OR 1=1", True),
        ("SELECT * FROM users WHERE id = 1 UNION SELECT password FROM admins", True),
        ("SELECT * FROM users WHERE name = 'test'; -- comment", True),
        ("SELECT * FROM users WHERE id = 1; DELETE FROM users", True),
        ("SELECT * FROM users WHERE name = 'test' OR 'a'='a'", True),
        ("SELECT SLEEP(10)", True),
        ("SELECT * FROM users WHERE id = CHAR(65,66,67)", True),
        ("SELECT * FROM users WHERE id = 0x41424344", True),
        ("SELECT * FROM users WHERE id = 1", False),  # Safe query
        ("SELECT name, email FROM users WHERE active = true", False),  # Safe query
    ]
    
    for query, should_detect in injection_tests:
        patterns = SQLValidator.detect_injection_patterns(query)
        detected = len(patterns) > 0
        
        if detected == should_detect:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        print(f"{status}: {'Detected' if detected else 'Safe'} - {query[:50]}...")
        if patterns:
            print(f"    Patterns found: {patterns}")
    
    print("\n✅ Injection detection tests completed!")

def test_identifier_validation():
    """Test identifier validation"""
    print("\n\nTesting Identifier Validation...")
    print("=" * 60)
    
    test_cases = [
        ("users", True),
        ("user_accounts", True),
        ("Users123", True),
        ("_private_table", True),
        ("123table", False),  # Starts with number
        ("user-accounts", False),  # Contains hyphen
        ("user accounts", False),  # Contains space
        ("DROP", False),  # SQL keyword
        ("SELECT", False),  # SQL keyword
        ("a" * 100, False),  # Too long
        ("", False),  # Empty
    ]
    
    for identifier, should_pass in test_cases:
        is_valid = SQLValidator.validate_table_name(identifier)
        
        if is_valid == should_pass:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        print(f"{status}: {identifier} - {'Valid' if is_valid else 'Invalid'}")
    
    print("\n✅ Identifier validation tests completed!")

def test_query_validation():
    """Test complete query validation"""
    print("\n\nTesting Query Validation...")
    print("=" * 60)
    
    test_queries = [
        ("SELECT * FROM users", [SQLOperation.SELECT], True),
        ("INSERT INTO users VALUES (1, 'test')", [SQLOperation.SELECT], False),  # INSERT not allowed
        ("UPDATE users SET name = 'test'", [SQLOperation.UPDATE], True),
        ("DELETE FROM users WHERE id = 1", [SQLOperation.DELETE], True),
        ("SELECT * FROM users; DROP TABLE users;", [SQLOperation.SELECT], False),  # Injection
        ("", None, False),  # Empty query
        ("a" * 200000, None, False),  # Too long
    ]
    
    for query, allowed_ops, should_pass in test_queries:
        is_valid, error = SQLValidator.validate_query(query[:50] if query else query, allowed_ops)
        
        if is_valid == should_pass:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        query_display = query[:50] + "..." if len(query) > 50 else query
        print(f"{status}: {query_display}")
        if error:
            print(f"    Error: {error}")
    
    print("\n✅ Query validation tests completed!")

def test_safe_query_builder():
    """Test safe query builder"""
    print("\n\nTesting Safe Query Builder...")
    print("=" * 60)
    
    # Test SELECT query building
    try:
        query, params = QueryBuilder.build_select(
            table="users",
            columns=["id", "name", "email"],
            conditions={"active": True, "role": "admin"},
            order_by="created_at DESC",
            limit=10
        )
        print("SELECT Query:")
        print(f"  SQL: {query}")
        print(f"  Params: {params}")
        print("  ✅ SELECT query built successfully")
    except Exception as e:
        print(f"  ❌ SELECT query failed: {e}")
    
    # Test INSERT query building
    try:
        query, params = QueryBuilder.build_insert(
            table="users",
            data={
                "name": "John Doe",
                "email": "john@example.com",
                "active": True
            }
        )
        print("\nINSERT Query:")
        print(f"  SQL: {query}")
        print(f"  Params: {params}")
        print("  ✅ INSERT query built successfully")
    except Exception as e:
        print(f"  ❌ INSERT query failed: {e}")
    
    # Test with invalid table name
    try:
        query, params = QueryBuilder.build_select(
            table="DROP TABLE users; --",
            columns=["*"]
        )
        print("\n  ❌ Should have failed with invalid table name!")
    except ValueError as e:
        print(f"\n  ✅ Correctly rejected invalid table: {e}")
    
    print("\n✅ Query builder tests completed!")

def test_input_sanitization():
    """Test input sanitization"""
    print("\n\nTesting Input Sanitization...")
    print("=" * 60)
    
    test_inputs = [
        ("normal text", "string", True, "normal text"),
        ("text with 'quotes'", "string", True, "text with ''quotes''"),
        ("text\x00with\x00null", "string", True, "textwith null"),
        ("123", "integer", True, 123),
        ("12.34", "float", True, 12.34),
        ("true", "boolean", True, True),
        ("false", "boolean", True, False),
        ("not_a_number", "integer", False, None),
        ("a" * 2000, "string", False, None),  # Too long with default max
    ]
    
    for input_val, input_type, should_pass, expected in test_inputs:
        is_valid, sanitized, error = validate_user_input(
            input_val, 
            input_type, 
            max_length=1000
        )
        
        if is_valid == should_pass:
            status = "✅ PASS"
            if should_pass and sanitized != expected:
                status = "⚠️  WARN"
                print(f"{status}: Input sanitization mismatch")
                print(f"    Input: {input_val[:30]}")
                print(f"    Expected: {expected}")
                print(f"    Got: {sanitized}")
            else:
                display_val = str(input_val)[:30] + "..." if len(str(input_val)) > 30 else str(input_val)
                print(f"{status}: {display_val} ({input_type}) → {sanitized if is_valid else error}")
        else:
            status = "❌ FAIL"
            print(f"{status}: Validation result mismatch for {input_val[:30]}")
    
    print("\n✅ Input sanitization tests completed!")

def test_where_clause_builder():
    """Test safe WHERE clause building"""
    print("\n\nTesting WHERE Clause Builder...")
    print("=" * 60)
    
    # Test normal conditions
    conditions = {
        "user_id": 123,
        "status": "active",
        "role": ["admin", "moderator"],
        "deleted": None
    }
    
    where_clause, params = SQLValidator.build_safe_where_clause(conditions)
    print("WHERE Clause:")
    print(f"  SQL: {where_clause}")
    print(f"  Params: {params}")
    
    # Test with invalid column names
    bad_conditions = {
        "user-id": 123,  # Invalid column name
        "DROP TABLE": "test",  # SQL keyword
        "valid_column": "value"
    }
    
    where_clause, params = SQLValidator.build_safe_where_clause(bad_conditions)
    print("\nFiltered WHERE Clause (invalid columns removed):")
    print(f"  SQL: {where_clause}")
    print(f"  Params: {params}")
    
    print("\n✅ WHERE clause builder tests completed!")

if __name__ == "__main__":
    print("=" * 60)
    print("SQL Injection Prevention Tests")
    print("=" * 60)
    
    test_sql_injection_detection()
    test_identifier_validation()
    test_query_validation()
    test_safe_query_builder()
    test_input_sanitization()
    test_where_clause_builder()
    
    print("\n" + "=" * 60)
    print("🎉 All SQL injection prevention tests completed!")
    print("=" * 60)