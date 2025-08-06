"""
Security utilities for credential encryption and management
"""
import os
import base64
import json
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)

class CredentialManager:
    """Manages encryption and decryption of database credentials"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize the credential manager with a master key
        
        Args:
            master_key: Master key for encryption. If not provided, generates from environment
        """
        self.master_key = master_key or os.environ.get('SQLAI_MASTER_KEY')
        
        if not self.master_key:
            # Generate a new master key if not exists
            self.master_key = self._generate_master_key()
            logger.warning("Generated new master key. Store it securely!")
            logger.info(f"Master key: {self.master_key}")
        
        self.cipher = self._create_cipher(self.master_key)
    
    def _generate_master_key(self) -> str:
        """Generate a new master key"""
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode('utf-8')
    
    def _create_cipher(self, master_key: str) -> Fernet:
        """Create a Fernet cipher from master key"""
        try:
            # Try to use the key directly if it's already a valid Fernet key
            key_bytes = base64.urlsafe_b64decode(master_key.encode())
            if len(key_bytes) == 32:
                return Fernet(base64.urlsafe_b64encode(key_bytes))
        except Exception:
            pass
        
        # Derive key from password using PBKDF2
        salt = b'sqlai_salt_2024'  # In production, use random salt per credential
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return Fernet(key)
    
    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """
        Encrypt database credentials
        
        Args:
            credentials: Dictionary containing database credentials
            
        Returns:
            Encrypted credentials as base64 string
        """
        try:
            json_str = json.dumps(credentials)
            encrypted = self.cipher.encrypt(json_str.encode())
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt credentials: {e}")
            raise
    
    def decrypt_credentials(self, encrypted_creds: str) -> Dict[str, Any]:
        """
        Decrypt database credentials
        
        Args:
            encrypted_creds: Encrypted credentials as base64 string
            
        Returns:
            Decrypted credentials dictionary
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_creds.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            raise
    
    def encrypt_password(self, password: str) -> str:
        """
        Encrypt a single password
        
        Args:
            password: Plain text password
            
        Returns:
            Encrypted password as base64 string
        """
        try:
            encrypted = self.cipher.encrypt(password.encode())
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt password: {e}")
            raise
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt a single password
        
        Args:
            encrypted_password: Encrypted password as base64 string
            
        Returns:
            Decrypted password
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_password.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt password: {e}")
            raise
    
    def validate_master_key(self, test_data: str = "test") -> bool:
        """
        Validate that the master key works correctly
        
        Args:
            test_data: Test string to encrypt/decrypt
            
        Returns:
            True if encryption/decryption works, False otherwise
        """
        try:
            encrypted = self.encrypt_password(test_data)
            decrypted = self.decrypt_password(encrypted)
            return decrypted == test_data
        except Exception:
            return False

# Global instance
_credential_manager: Optional[CredentialManager] = None

def get_credential_manager() -> CredentialManager:
    """Get or create the global credential manager instance"""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager

def encrypt_connection_string(conn_string: str) -> str:
    """
    Encrypt a database connection string
    
    Args:
        conn_string: Plain text connection string
        
    Returns:
        Encrypted connection string
    """
    manager = get_credential_manager()
    return manager.encrypt_password(conn_string)

def decrypt_connection_string(encrypted_conn_string: str) -> str:
    """
    Decrypt a database connection string
    
    Args:
        encrypted_conn_string: Encrypted connection string
        
    Returns:
        Plain text connection string
    """
    manager = get_credential_manager()
    return manager.decrypt_password(encrypted_conn_string)