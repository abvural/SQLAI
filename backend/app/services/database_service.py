"""
Database service for managing connections and credentials
"""
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import logging
from pathlib import Path

from app.utils.security import get_credential_manager

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for managing database connections"""
    
    def __init__(self, config_file: str = "config/database_connections.json"):
        """
        Initialize database service
        
        Args:
            config_file: Path to database connections configuration file
        """
        self.config_file = Path(config_file)
        self.credential_manager = get_credential_manager()
        self.connections: Dict[str, Dict[str, Any]] = {}
        self._ensure_config_dir()
        self._load_connections()
    
    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_connections(self):
        """Load saved database connections"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.connections = data.get('databases', {})
                    logger.info(f"Loaded {len(self.connections)} database connections")
            except Exception as e:
                logger.error(f"Failed to load connections: {e}")
                self.connections = {}
        else:
            self.connections = {}
            self._save_connections()
    
    def _save_connections(self):
        """Save database connections to file"""
        try:
            data = {
                'databases': self.connections,
                'updated_at': datetime.utcnow().isoformat()
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.connections)} database connections")
        except Exception as e:
            logger.error(f"Failed to save connections: {e}")
    
    def add_connection(
        self,
        name: str,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        ssl_mode: str = "prefer"
    ) -> str:
        """
        Add a new database connection
        
        Args:
            name: Connection display name
            host: Database host
            port: Database port
            database: Database name
            username: Username
            password: Plain text password (will be encrypted)
            ssl_mode: SSL mode
            
        Returns:
            Connection ID
        """
        conn_id = str(uuid.uuid4())
        
        # Encrypt password
        encrypted_password = self.credential_manager.encrypt_password(password)
        
        connection = {
            'id': conn_id,
            'name': name,
            'host': host,
            'port': port,
            'database': database,
            'username': username,
            'password': encrypted_password,
            'ssl_mode': ssl_mode,
            'created_at': datetime.utcnow().isoformat(),
            'last_connected': None,
            'schema_analyzed': False,
            'status': 'configured'
        }
        
        self.connections[conn_id] = connection
        self._save_connections()
        
        logger.info(f"Added connection: {name} ({conn_id})")
        return conn_id
    
    def get_connection(self, conn_id: str) -> Optional[Dict[str, Any]]:
        """
        Get connection details (with decrypted password)
        
        Args:
            conn_id: Connection ID
            
        Returns:
            Connection details with decrypted password
        """
        if conn_id not in self.connections:
            return None
        
        conn = self.connections[conn_id].copy()
        
        # Decrypt password
        try:
            conn['password'] = self.credential_manager.decrypt_password(conn['password'])
        except Exception as e:
            logger.error(f"Failed to decrypt password for {conn_id}: {e}")
            conn['password'] = None
        
        return conn
    
    def get_connection_safe(self, conn_id: str) -> Optional[Dict[str, Any]]:
        """
        Get connection details without password
        
        Args:
            conn_id: Connection ID
            
        Returns:
            Connection details without password
        """
        if conn_id not in self.connections:
            return None
        
        conn = self.connections[conn_id].copy()
        conn.pop('password', None)
        return conn
    
    def list_connections(self) -> List[Dict[str, Any]]:
        """
        List all connections (without passwords)
        
        Returns:
            List of connections without passwords
        """
        connections = []
        for conn_id, conn in self.connections.items():
            safe_conn = conn.copy()
            safe_conn.pop('password', None)
            connections.append(safe_conn)
        return connections
    
    def update_connection(
        self,
        conn_id: str,
        name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ssl_mode: Optional[str] = None
    ) -> bool:
        """
        Update connection details
        
        Args:
            conn_id: Connection ID
            Other args: Fields to update
            
        Returns:
            True if updated successfully
        """
        if conn_id not in self.connections:
            return False
        
        conn = self.connections[conn_id]
        
        if name is not None:
            conn['name'] = name
        if host is not None:
            conn['host'] = host
        if port is not None:
            conn['port'] = port
        if database is not None:
            conn['database'] = database
        if username is not None:
            conn['username'] = username
        if password is not None:
            conn['password'] = self.credential_manager.encrypt_password(password)
        if ssl_mode is not None:
            conn['ssl_mode'] = ssl_mode
        
        conn['updated_at'] = datetime.utcnow().isoformat()
        
        self._save_connections()
        logger.info(f"Updated connection: {conn_id}")
        return True
    
    def delete_connection(self, conn_id: str) -> bool:
        """
        Delete a connection
        
        Args:
            conn_id: Connection ID
            
        Returns:
            True if deleted successfully
        """
        if conn_id not in self.connections:
            return False
        
        del self.connections[conn_id]
        self._save_connections()
        logger.info(f"Deleted connection: {conn_id}")
        return True
    
    def update_connection_status(
        self,
        conn_id: str,
        status: str,
        last_connected: Optional[datetime] = None
    ) -> bool:
        """
        Update connection status
        
        Args:
            conn_id: Connection ID
            status: New status
            last_connected: Last connection time
            
        Returns:
            True if updated successfully
        """
        if conn_id not in self.connections:
            return False
        
        self.connections[conn_id]['status'] = status
        if last_connected:
            self.connections[conn_id]['last_connected'] = last_connected.isoformat()
        
        self._save_connections()
        return True
    
    def mark_schema_analyzed(self, conn_id: str) -> bool:
        """
        Mark connection as having schema analyzed
        
        Args:
            conn_id: Connection ID
            
        Returns:
            True if updated successfully
        """
        if conn_id not in self.connections:
            return False
        
        self.connections[conn_id]['schema_analyzed'] = True
        self.connections[conn_id]['schema_analyzed_at'] = datetime.utcnow().isoformat()
        
        self._save_connections()
        return True

# Global instance
_database_service: Optional[DatabaseService] = None

def get_database_service() -> DatabaseService:
    """Get or create the global database service instance"""
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service