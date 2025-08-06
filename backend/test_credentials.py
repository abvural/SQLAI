#!/usr/bin/env python3
"""
Test credential encryption and database service
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.security import CredentialManager
from app.services.database_service import DatabaseService

def test_credential_encryption():
    """Test credential encryption/decryption"""
    print("Testing Credential Encryption...")
    
    # Create credential manager
    manager = CredentialManager("test_master_key_123")
    
    # Test password encryption
    original_password = "myuser01"
    encrypted = manager.encrypt_password(original_password)
    decrypted = manager.decrypt_password(encrypted)
    
    print(f"Original: {original_password}")
    print(f"Encrypted: {encrypted[:20]}...")
    print(f"Decrypted: {decrypted}")
    assert original_password == decrypted, "Password encryption/decryption failed!"
    
    # Test credentials dictionary
    creds = {
        "host": "172.17.12.76",
        "port": 5432,
        "database": "postgres",
        "username": "myuser",
        "password": "myuser01"
    }
    
    encrypted_creds = manager.encrypt_credentials(creds)
    decrypted_creds = manager.decrypt_credentials(encrypted_creds)
    
    print(f"\nOriginal credentials: {creds}")
    print(f"Encrypted: {encrypted_creds[:30]}...")
    print(f"Decrypted: {decrypted_creds}")
    assert creds == decrypted_creds, "Credentials encryption/decryption failed!"
    
    print("\n✅ Credential encryption tests passed!")

def test_database_service():
    """Test database service"""
    print("\nTesting Database Service...")
    
    # Set master key for testing
    os.environ['SQLAI_MASTER_KEY'] = 'test_master_key_123'
    
    # Create service
    service = DatabaseService("test_config.json")
    
    # Add connection
    conn_id = service.add_connection(
        name="Test Database",
        host="172.17.12.76",
        port=5432,
        database="postgres",
        username="myuser",
        password="myuser01",
        ssl_mode="prefer"
    )
    
    print(f"Added connection: {conn_id}")
    
    # Get connection with decrypted password
    conn = service.get_connection(conn_id)
    print(f"Retrieved connection: {conn['name']}")
    print(f"Decrypted password: {conn['password']}")
    assert conn['password'] == "myuser01", "Password decryption failed!"
    
    # Get safe connection (no password)
    safe_conn = service.get_connection_safe(conn_id)
    print(f"Safe connection: {safe_conn['name']}")
    assert 'password' not in safe_conn, "Safe connection should not have password!"
    
    # List connections
    connections = service.list_connections()
    print(f"Total connections: {len(connections)}")
    assert len(connections) == 1, "Should have 1 connection"
    
    # Delete connection
    service.delete_connection(conn_id)
    connections = service.list_connections()
    assert len(connections) == 0, "Should have 0 connections after delete"
    
    # Clean up test file
    if os.path.exists("test_config.json"):
        os.remove("test_config.json")
    
    print("\n✅ Database service tests passed!")

if __name__ == "__main__":
    test_credential_encryption()
    test_database_service()
    print("\n🎉 All tests passed!")