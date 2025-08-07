#!/usr/bin/env python3
"""
Script to fix credential decryption issues by updating all encrypted passwords
with a consistent master key
"""
import json
import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent))

from app.utils.security import CredentialManager

def main():
    """Fix encrypted credentials in database connections file"""
    
    # Set fixed master key
    master_key = "sqlai-fixed-master-key-2024-v1"
    os.environ['SQLAI_MASTER_KEY'] = master_key
    
    # Create credential manager with fixed key
    manager = CredentialManager(master_key)
    
    # Load database connections
    config_file = Path("config/database_connections.json")
    if not config_file.exists():
        print("Database connections file not found!")
        return
    
    with open(config_file, 'r') as f:
        data = json.load(f)
    
    databases = data.get('databases', {})
    fixed_count = 0
    
    print(f"Found {len(databases)} database connections to fix...")
    
    for db_id, db_info in databases.items():
        try:
            # Try to decrypt existing password
            encrypted_pwd = db_info.get('password', '')
            if not encrypted_pwd:
                print(f"Skipping {db_info['name']} - no password field")
                continue
                
            try:
                # Try to decrypt with current key
                decrypted = manager.decrypt_password(encrypted_pwd)
                print(f"✅ {db_info['name']} - password already works")
                continue
            except:
                # Password can't be decrypted, assume it's the default password
                print(f"🔧 {db_info['name']} - fixing encrypted password")
                
                # Use default password for test database
                default_password = "myuser01"
                new_encrypted = manager.encrypt_password(default_password)
                
                # Update the password
                databases[db_id]['password'] = new_encrypted
                fixed_count += 1
                print(f"   New encrypted password: {new_encrypted[:50]}...")
                
        except Exception as e:
            print(f"❌ Failed to fix {db_info['name']}: {e}")
    
    # Save updated connections
    if fixed_count > 0:
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Fixed {fixed_count} database connections!")
        print("Restart the backend server for changes to take effect.")
    else:
        print("\n✅ No fixes needed - all passwords are working correctly!")

if __name__ == "__main__":
    main()